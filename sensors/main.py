# main_control.py
"""
Main control loop - ties everything together.
Coordinates sensors, navigation, and motors.
"""
import time
import config
from imu import init_imu
from magnetometer import init_mag
from gpsmanager import init_gps, get_position
from coordinate_transform import set_reference_point, latlon_to_xy
from navigation import Navigator
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
        # Get navigation command FIRST
        command, speed = self.nav.get_navigation_command()
        
        # Only update position when moving forward (not during turns)
        if command == 'forward':
            state = self.nav.update_position()
            if state is None:
                return  # First iteration, skip
        else:
            # During turns, just get current state without updating position
            from magnetometer import get_heading_basic
            state = {
                'x': self.nav.x,
                'y': self.nav.y,
                'vx': self.nav.vx,
                'vy': self.nav.vy,
                'heading': get_heading_basic(),
                'ax_body': 0, 'ay_body': 0, 'az_body': 0,
                'ax_earth': 0, 'ay_earth': 0
            }
        
        # Check if GPS resync needed
        if self.nav.should_resync_gps():
            self.update_from_gps()
            self.last_gps_update = time.time()
        
        time.sleep(0.1)
        
        # Execute motor command
        if command == 'forward':
            motor_helper.forward(speed)
            time.sleep(0.1)
        elif command == 'turn_left':
            motor_helper.turn_left(speed)
            time.sleep(0.4)
            motor_helper.stop()
            time.sleep(0.1)
        elif command == 'turn_right':
            motor_helper.turn_right(speed)
            time.sleep(0.4)
            motor_helper.stop()
            time.sleep(0.1)
        elif command == 'stop':
            motor_helper.stop()
            self.running = False
        
        # Debug print
        if config.DEBUG_PRINT_NAVIGATION:
            dist = self.nav.get_distance_to_destination()
            heading_err = self.nav.get_heading_error()
            print(f"Pos:({state['x']:.1f},{state['y']:.1f}) "
                f"Heading:{state['heading']:.1f}° "
                f"Dist:{dist:.1f}m HErr:{heading_err:.1f}° Cmd:{command}")
    
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

# Standalone test/demo
if __name__ == "__main__":
    # Create controller
    rover = RoverController()
    
    # Set a test destination (+- east / west, +- North/South from start)
    rover.set_destination_xy(-3, 0)
    
    # Run navigation
    rover.run()