# main_control.py
"""
Main control loop - ties everything together.
Coordinates sensors, navigation, motors, and logging.
"""
import time
import config
from imu import init_imu
from magnetometer import init_mag
from gpsmanager import init_gps, get_position
from coordinate_transform import set_reference_point, latlon_to_xy
from navigation import Navigator
from datalogger import init_logger, log_data, close_logger, flush
import motor_helper


class RoverController:
    def __init__(self):
        print("Initializing rover systems...")
        
        # Initialize sensors
        init_imu()
        init_mag()
        init_gps()
        
        # Initialize navigator
        self.nav = Navigator()
        
        # Initialize logger
        if config.LOG_ENABLED:
            init_logger()
        
        # Get initial GPS position and set as reference
        lat, lon = None, None
        attempts = 0
        maxattempts = 5
        while (lat is None or lon is None) and attempts < maxattempts:
            lat, lon = get_position()
            if lat is None or lon is None:
                time.sleep(1)
                attempts += 1
                
        
        set_reference_point(lat, lon)
        self.nav.reset_position(0, 0)  # Start at origin
        
        print(f"Rover initialized at: {lat:.6f}, {lon:.6f}")
        
        # State tracking
        self.last_gps_update = time.time()
        self.running = False
    
    def set_destination_latlon(self, dest_lat, dest_lon):
        """Set destination using GPS coordinates."""
        dest_x, dest_y = latlon_to_xy(dest_lat, dest_lon)
        self.nav.set_destination(dest_x, dest_y)
        print(f"Destination: {dest_lat:.6f}, {dest_lon:.6f} -> ({dest_x:.1f}m, {dest_y:.1f}m)")
    
    def set_destination_xy(self, x, y):
        """Set destination using local XY coordinates."""
        self.nav.set_destination(x, y)
    
    def update_from_gps(self):
        """Resync position from GPS (called periodically)."""
        lat, lon = get_position()
        if lat is not None and lon is not None:
            x, y = latlon_to_xy(lat, lon)
            self.nav.reset_position(x, y)
            if config.DEBUG_PRINT_NAVIGATION:
                print(f"GPS resync: ({x:.2f}, {y:.2f})")
            return lat, lon
        return None, None
    
    def control_loop(self):
        """Main control loop - call this repeatedly."""
        # Update navigation state from IMU
        state = self.nav.update_position()
        
        if state is None:
            return  # First iteration, skip
        
        # Check if GPS resync needed
        lat, lon = None, None
        if self.nav.should_resync_gps():
            lat, lon = self.update_from_gps()
            self.last_gps_update = time.time()
        
        # Get navigation command
        command, speed = self.nav.get_navigation_command()
        time.sleep(1)
        
        # Execute motor command
        if command == 'forward':
            motor_helper.forward(speed)
        elif command == 'turn_left':
            motor_helper.turn_left(speed)
        elif command == 'turn_right':
            motor_helper.turn_right(speed)
        elif command == 'stop':
            motor_helper.stop()
            self.running = False
        
        # Debug print
        if config.DEBUG_PRINT_NAVIGATION:
            dist = self.nav.get_distance_to_destination()
            print(f"Pos:({state['x']:.1f},{state['y']:.1f}) "
                  f"Dist:{dist:.1f}m Cmd:{command}")
        
        # Log data
        if config.LOG_ENABLED:
            log_data(
                lat=lat,
                lon=lon,
                x_calc=state['x'],
                y_calc=state['y'],
                vx=state['vx'],
                vy=state['vy'],
                ax_body=state['ax_body'],
                ay_body=state['ay_body'],
                az_body=state['az_body'],
                ax_earth=state['ax_earth'],
                ay_earth=state['ay_earth'],
                heading=state['heading'],
                target_bearing=self.nav.get_bearing_to_destination(),
                heading_error=self.nav.get_heading_error(),
                distance_to_dest=self.nav.get_distance_to_destination(),
                motor_command=command
            )
    
    def run(self):
        """Run the control loop until destination reached."""
        self.running = True
        loop_time = 1.0 / config.IMU_FREQUENCY
        
        print("Starting navigation...")
        
        try:
            while self.running and not self.nav.has_reached_destination():
                start = time.time()
                
                self.control_loop()
                
                # Maintain loop timing
                elapsed = time.time() - start
                if elapsed < loop_time:
                    time.sleep(loop_time - elapsed)
            
            # Reached destination or stopped
            motor_helper.stop()
            print("Navigation complete!")
            
        except KeyboardInterrupt:
            print("\nStopping...")
            motor_helper.stop()
        
        finally:
            # Flush and close logger
            if config.LOG_ENABLED:
                flush()
                close_logger()

# Standalone test/demo
if __name__ == "__main__":
    # Create controller
    rover = RoverController()
    
    # Set a test destination (0m east, 1m North from start)
    rover.set_destination_xy(0, 10)
    
    # Run navigation
    rover.run()