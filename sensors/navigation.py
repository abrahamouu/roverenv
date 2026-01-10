# navigation.py
"""
Core navigation using IMU double integration with magnetometer drift compensation.
Implements relative positioning between GPS waypoints.
"""
import time
import config
from imu import get_accel
from heading import get_heading_tilt_compensated
from coordinate_transform import (
    body_to_earth_frame, 
    angle_difference, 
    distance_2d, 
    bearing_to_point
)

class Navigator:
    def __init__(self):
        # Current state
        self.x = 0.0  # East position (meters)
        self.y = 0.0  # North position (meters)
        self.vx = 0.0  # East velocity (m/s)
        self.vy = 0.0  # North velocity (m/s)
        
        # Destination
        self.dest_x = None
        self.dest_y = None
        
        # Timing
        self.last_update_time = None
        self.dt = 1.0 / config.IMU_FREQUENCY
        
        # GPS resync tracking
        self.last_gps_sync = time.time()
        
        print(f"Navigator initialized (IMU freq: {config.IMU_FREQUENCY}Hz)")
    
    def set_destination(self, x, y):
        """Set destination in local XY coordinates (meters)."""
        self.dest_x = x
        self.dest_y = y
        dist = self.get_distance_to_destination()
        print(f"Destination set: ({x:.1f}, {y:.1f}), distance: {dist:.2f}m")
    
    def reset_position(self, x, y):
        """
        Reset position (e.g., from GPS update).
        Also resets velocity to prevent accumulated drift.
        """
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.last_gps_sync = time.time()
        print(f"Position reset: ({x:.2f}, {y:.2f})")
    
    def update_position(self):
        """
        Main navigation update - double integrate IMU acceleration.
        Call this at IMU_FREQUENCY Hz.
        """
        # Get current time
        current_time = time.time()
        if self.last_update_time is None:
            self.last_update_time = current_time
            return
        
        # Calculate actual dt (in case loop timing varies)
        dt = current_time - self.last_update_time
        self.last_update_time = current_time
        
        # Read sensors
        ax_body, ay_body, az_body = get_accel()
        heading = get_heading_tilt_compensated()
        
        # Remove gravity from z-axis and apply calibration offsets
        az_body -= 9.81
        ax_body -= config.ACCEL_BIAS_X
        ay_body -= config.ACCEL_BIAS_Y
        
        # Transform acceleration from body frame to earth frame
        ax_earth, ay_earth = body_to_earth_frame(ax_body, ay_body, heading)
        
        # Double integration: accel -> velocity -> position
        # Velocity update with decay (simulates friction/drag)
        self.vx = self.vx * config.VELOCITY_DECAY_FACTOR + ax_earth * dt
        self.vy = self.vy * config.VELOCITY_DECAY_FACTOR + ay_earth * dt
        
        # Position update
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # Return state for logging
        return {
            'x': self.x,
            'y': self.y,
            'vx': self.vx,
            'vy': self.vy,
            'ax_body': ax_body,
            'ay_body': ay_body,
            'az_body': az_body,
            'ax_earth': ax_earth,
            'ay_earth': ay_earth,
            'heading': heading
        }
    
    def get_distance_to_destination(self):
        """Calculate distance to destination in meters."""
        if self.dest_x is None or self.dest_y is None:
            return float('inf')
        return distance_2d(self.x, self.y, self.dest_x, self.dest_y)
    
    def get_bearing_to_destination(self):
        """Calculate bearing to destination (0-360°)."""
        if self.dest_x is None or self.dest_y is None:
            return None
        return bearing_to_point(self.x, self.y, self.dest_x, self.dest_y)
    
    def get_heading_error(self):
        """
        Calculate heading error (how much to turn).
        Returns: degrees to turn (-180 to +180)
            Positive = need to turn right
            Negative = need to turn left
        """
        target_bearing = self.get_bearing_to_destination()
        if target_bearing is None:
            return 0.0
        
        current_heading = get_heading_tilt_compensated()
        return angle_difference(target_bearing, current_heading)
    
    def has_reached_destination(self):
        """Check if within epsilon of destination."""
        dist = self.get_distance_to_destination()
        return dist < config.POSITION_EPSILON
    
    def should_resync_gps(self):
        """Check if GPS resync is needed (time-based or drift threshold)."""
        time_since_sync = time.time() - self.last_gps_sync
        return time_since_sync > config.GPS_UPDATE_INTERVAL
    
    def get_navigation_command(self):
        """
        High-level navigation decision.
        Returns: ('forward'|'turn_left'|'turn_right'|'stop', speed)
        """
        if self.has_reached_destination():
            return 'stop', 0.0
        
        heading_error = self.get_heading_error()
        
        # If heading is way off, turn in place
        if abs(heading_error) > config.HEADING_TOLERANCE:
            if heading_error > 0:
                return 'turn_right', config.TURN_SPEED
            else:
                return 'turn_left', config.TURN_SPEED
        
        # Heading is good enough, move forward
        return 'forward', config.BASE_SPEED

# Test mode
if __name__ == "__main__":
    import config
    from imu import init_imu
    from magnetometer import init_mag
    
    # Initialize sensors
    init_imu()
    init_mag()
    
    # Create navigator
    nav = Navigator()
    
    # Set a test destination (10m North, 5m East)
    nav.set_destination(5, 10)
    
    print("\nRunning navigation test for 5 seconds...")
    print("(Rover should be stationary, so position should stay near 0,0)\n")
    
    try:
        for i in range(50):  # 5 seconds at 10Hz
            state = nav.update_position()

            if state is None:
                time.sleep(0.1)
                continue
            
            if i % 10 == 0:  # Print every second
                dist = nav.get_distance_to_destination()
                bearing = nav.get_bearing_to_destination()
                heading_err = nav.get_heading_error()
                cmd, speed = nav.get_navigation_command()
                
                print(f"Pos: ({state['x']:.2f}, {state['y']:.2f})m | "
                      f"Vel: ({state['vx']:.2f}, {state['vy']:.2f})m/s | "
                      f"Dist: {dist:.2f}m | "
                      f"Heading err: {heading_err:.1f}° | "
                      f"Cmd: {cmd}")
            
            time.sleep(0.1)  # 10Hz update
    
    except KeyboardInterrupt:
        print("\nTest stopped")
    
    print(f"\nFinal position: ({nav.x:.2f}, {nav.y:.2f})")
    print("(Should be close to 0,0 if stationary)")