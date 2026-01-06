# navigation.py
import time
import math
import numpy as np
from typing import Optional, Dict, List
from config import (
    POSITION_EPSILON,
    GPS_RECHECK_INTERVAL,
    DRIFT_THRESHOLD,
    IMU_FREQUENCY,
    ENABLE_DEBUG_LOGGING,
    LOG_FREQUENCY,
    MIN_SATELLITES,
    MAX_GPS_ERROR
)
import gps
import sensor_fusion


class Navigation:
    """
    High-level navigation system implementing waypoint-based navigation
    with IMU/Magnetometer sensor fusion and periodic GPS recalibration.
    
    Implements your core algorithm:
        D_relative = P_destination - P_current
        Check: |D_traveled - D_relative| < epsilon
    """
    
    def __init__(self):
        self.p_current = None  # Current GPS position (waypoint)
        self.p_destination = None  # Destination GPS position
        self.d_relative = None  # Vector from current to destination
        self.d_relative_magnitude = None  # Distance to destination
        
        self.d_traveled = np.array([0.0, 0.0])  # Distance traveled from p_current (IMU-based)
        
        self.last_gps_time = 0.0
        self.start_time = None
        self.navigation_active = False
        
        self.waypoints = []  # List of waypoints for multi-point navigation
        self.current_waypoint_index = 0
        
        # Statistics
        self.total_distance_traveled = 0.0
        self.gps_recalibration_count = 0
        
    
    def initialize(self):
        """
        Initialize all sensors and get starting GPS position.
        
        Returns:
            True if initialization successful
        """
        print("\n" + "="*60)
        print("NAVIGATION SYSTEM INITIALIZATION")
        print("="*60)
        
        # Initialize GPS
        print("\n1. Initializing GPS...")
        if not gps.init_gps():
            print("   ✗ GPS initialization failed!")
            return False
        print("   ✓ GPS initialized")
        
        # Initialize sensor fusion (IMU + Magnetometer)
        print("\n2. Initializing IMU and Magnetometer...")
        if not sensor_fusion.init_fusion():
            print("   ✗ Sensor fusion initialization failed!")
            return False
        print("   ✓ Sensor fusion initialized")
        
        # Get initial GPS position
        print("\n3. Acquiring starting position...")
        self.p_current = gps.get_waypoint("Starting Position", retries=5)
        
        if not self.p_current:
            print("   ✗ Failed to acquire starting position!")
            return False
        
        print(f"   ✓ Starting position: ({self.p_current['lat']:.6f}, {self.p_current['lon']:.6f})")
        print(f"     GPS accuracy: ±{self.p_current['error']:.1f}m")
        
        # Set as reference point for sensor fusion
        sensor_fusion.set_reference_point(self.p_current)
        self.last_gps_time = time.time()
        
        print("\n" + "="*60)
        print("INITIALIZATION COMPLETE")
        print("="*60 + "\n")
        
        return True
    
    
    def set_destination(self, destination=None):
        """
        Set navigation destination.
        
        Args:
            destination: GPS dict {'lat': lat, 'lon': lon} or None to acquire from GPS
        
        Returns:
            True if destination set successfully
        """
        if destination is None:
            print("\nAcquiring destination position...")
            self.p_destination = gps.get_waypoint("Destination", retries=3)
        else:
            self.p_destination = destination
        
        if not self.p_destination:
            print("Failed to set destination!")
            return False
        
        # Calculate D_relative = P_destination - P_current
        self._calculate_d_relative()
        
        print(f"Destination set: ({self.p_destination['lat']:.6f}, {self.p_destination['lon']:.6f})")
        print(f"Distance to destination: {self.d_relative_magnitude:.1f} meters")
        print(f"Bearing: {self._calculate_bearing():.1f}°")
        
        return True
    
    
    def add_waypoint(self, waypoint):
        """
        Add a waypoint to the navigation route.
        
        Args:
            waypoint: GPS dict {'lat': lat, 'lon': lon, 'name': optional}
        """
        self.waypoints.append(waypoint)
        print(f"Waypoint added: {waypoint.get('name', f'Waypoint {len(self.waypoints)}')}")
    
    
    def start_navigation(self):
        """
        Start active navigation to destination.
        """
        if self.p_destination is None:
            print("ERROR: No destination set! Call set_destination() first.")
            return False
        
        self.navigation_active = True
        self.start_time = time.time()
        self.total_distance_traveled = 0.0
        
        print("\n" + "="*60)
        print("NAVIGATION STARTED")
        print("="*60)
        print(f"From: ({self.p_current['lat']:.6f}, {self.p_current['lon']:.6f})")
        print(f"To:   ({self.p_destination['lat']:.6f}, {self.p_destination['lon']:.6f})")
        print(f"Distance: {self.d_relative_magnitude:.1f}m")
        print(f"Bearing: {self._calculate_bearing():.1f}°")
        print("="*60 + "\n")
        
        return True
    
    
    def update(self, dt=None):
        """
        Main navigation update loop - call this at IMU_FREQUENCY Hz.
        
        Args:
            dt: Time delta (if None, uses 1/IMU_FREQUENCY)
        
        Returns:
            dict with navigation status
        """
        if not self.navigation_active:
            return None
        
        if dt is None:
            dt = 1.0 / IMU_FREQUENCY
        
        # Update sensor fusion (IMU + Magnetometer)
        fusion_result = sensor_fusion.update(dt)
        
        # Get D_traveled from sensor fusion
        self.d_traveled = fusion_result['position']
        
        # Check if GPS recalibration is needed
        if self.should_recalibrate():
            self._recalibrate_from_gps()
        
        # Check arrival at destination
        arrived = self.check_arrival()
        
        # Prepare status
        status = {
            'arrived': arrived,
            'position': self.d_traveled.copy(),
            'destination_distance': self._calculate_remaining_distance(),
            'heading': fusion_result['heading'],
            'bearing_to_dest': self._calculate_bearing(),
            'heading_error': fusion_result['heading_error'],
            'velocity': fusion_result['velocity'],
            'gps_recalibrations': self.gps_recalibration_count,
            'elapsed_time': time.time() - self.start_time if self.start_time else 0
        }
        
        # Debug logging
        if ENABLE_DEBUG_LOGGING:
            self._log_status(status)
        
        return status
    
    
    def check_arrival(self):
        """
        Check if destination has been reached using your epsilon criterion:
            |D_traveled - D_relative| < epsilon
        
        Returns:
            True if arrived at destination
        """
        if self.d_relative is None:
            return False
        
        # Calculate error: difference between where we should be and where we are
        error = np.linalg.norm(self.d_traveled - self.d_relative)
        
        # Check against epsilon threshold
        arrived = error < POSITION_EPSILON
        
        if arrived:
            print("\n" + "="*60)
            print("🎯 DESTINATION REACHED!")
            print("="*60)
            print(f"Final error: {error:.2f}m (threshold: {POSITION_EPSILON}m)")
            print(f"Total distance traveled: {self.total_distance_traveled:.1f}m")
            print(f"GPS recalibrations: {self.gps_recalibration_count}")
            print(f"Time elapsed: {time.time() - self.start_time:.1f}s")
            print("="*60 + "\n")
            
            self.navigation_active = False
        
        return arrived
    
    
    def should_recalibrate(self):
        """
        Determine if GPS recalibration is needed based on:
        1. Time elapsed since last GPS fix
        2. Estimated drift magnitude
        
        Returns:
            True if recalibration needed
        """
        current_time = time.time()
        
        # Time-based recalibration
        if (current_time - self.last_gps_time) >= GPS_RECHECK_INTERVAL:
            return True
        
        # Drift-based recalibration
        estimated_drift = sensor_fusion.get_distance_from_reference()
        if estimated_drift > DRIFT_THRESHOLD:
            print(f"WARNING: Drift exceeds threshold ({estimated_drift:.1f}m > {DRIFT_THRESHOLD}m)")
            return True
        
        return False
    
    
    def _recalibrate_from_gps(self):
        """
        Recalibrate position using GPS fix.
        This corrects for magnitude drift that can't be fixed by heading alone.
        """
        print("\n[GPS Recalibration]")
        
        # Get fresh GPS reading
        gps_fix = gps.get_gps(timeout=5.0)
        
        if not gps_fix:
            print("  ✗ GPS fix failed - continuing with IMU")
            return
        
        # Validate GPS quality
        if gps_fix.get('satellites', 0) < MIN_SATELLITES:
            print(f"  ✗ Insufficient satellites ({gps_fix['satellites']} < {MIN_SATELLITES})")
            return
        
        error = max(gps_fix.get('epx', 999), gps_fix.get('epy', 999))
        if error > MAX_GPS_ERROR:
            print(f"  ✗ GPS error too high ({error:.1f}m > {MAX_GPS_ERROR}m)")
            return
        
        # Recalibrate sensor fusion
        sensor_fusion.recalibrate_from_gps(gps_fix, reset_position=False)
        
        self.last_gps_time = time.time()
        self.gps_recalibration_count += 1
        
        print(f"  ✓ Recalibration #{self.gps_recalibration_count} complete")
        print(f"    Satellites: {gps_fix['satellites']}, Error: ±{error:.1f}m")
    
    
    def _calculate_d_relative(self):
        """
        Calculate D_relative = P_destination - P_current
        This is the vector from current position to destination.
        """
        if not self.p_current or not self.p_destination:
            return
        
        # Convert GPS to meters
        self.d_relative = self._gps_to_meters(
            self.p_destination,
            self.p_current
        )
        
        self.d_relative_magnitude = np.linalg.norm(self.d_relative)
    
    
    def _calculate_remaining_distance(self):
        """
        Calculate remaining distance to destination.
        
        Returns:
            Distance in meters
        """
        if self.d_relative is None:
            return None
        
        remaining = self.d_relative - self.d_traveled
        return np.linalg.norm(remaining)
    
    
    def _calculate_bearing(self):
        """
        Calculate bearing (direction) to destination in degrees.
        0° = North, 90° = East, 180° = South, 270° = West
        
        Returns:
            Bearing in degrees (0-360)
        """
        if self.d_relative is None:
            return None
        
        # atan2(East, North) gives bearing
        bearing_rad = math.atan2(self.d_relative[0], self.d_relative[1])
        bearing_deg = math.degrees(bearing_rad)
        
        # Normalize to 0-360
        if bearing_deg < 0:
            bearing_deg += 360
        
        return bearing_deg
    
    
    def _gps_to_meters(self, gps_pos, reference):
        """
        Convert GPS coordinates to meters from reference point.
        
        Args:
            gps_pos: dict {'lat': lat, 'lon': lon}
            reference: dict {'lat': lat, 'lon': lon}
        
        Returns:
            np.array([x, y]) in meters (East, North)
        """
        delta_lat = gps_pos['lat'] - reference['lat']
        delta_lon = gps_pos['lon'] - reference['lon']
        
        meters_per_degree_lat = 111000.0
        meters_per_degree_lon = 111000.0 * math.cos(math.radians(reference['lat']))
        
        x = delta_lon * meters_per_degree_lon  # East
        y = delta_lat * meters_per_degree_lat  # North
        
        return np.array([x, y])
    
    
    def _log_status(self, status):
        """
        Log navigation status for debugging.
        """
        # Only log at LOG_FREQUENCY
        if not hasattr(self, '_last_log_time'):
            self._last_log_time = 0
        
        current_time = time.time()
        if (current_time - self._last_log_time) < (1.0 / LOG_FREQUENCY):
            return
        
        self._last_log_time = current_time
        
        pos = status['position']
        dist = status['destination_distance']
        heading = status['heading']
        bearing = status['bearing_to_dest']
        
        print(f"[{status['elapsed_time']:6.1f}s] "
              f"Pos: [{pos[0]:6.1f}, {pos[1]:6.1f}]m | "
              f"Dist: {dist:5.1f}m | "
              f"Head: {heading:5.1f}° | "
              f"Bear: {bearing:5.1f}°")
    
    
    def stop_navigation(self):
        """
        Stop active navigation.
        """
        self.navigation_active = False
        print("\nNavigation stopped")
    
    
    def get_status_summary(self):
        """
        Get complete navigation status summary.
        
        Returns:
            dict with comprehensive status info
        """
        return {
            'active': self.navigation_active,
            'current_position': self.p_current,
            'destination': self.p_destination,
            'position_traveled': self.d_traveled.tolist() if self.d_traveled is not None else None,
            'distance_to_destination': self._calculate_remaining_distance(),
            'bearing': self._calculate_bearing(),
            'gps_recalibrations': self.gps_recalibration_count,
            'elapsed_time': time.time() - self.start_time if self.start_time else 0,
            'fusion_status': sensor_fusion.get_status()
        }


# ===== STANDALONE TEST MODE =====

def test_navigation():
    """
    Test navigation system with simulated waypoints.
    For real use, walk/drive to actual destination.
    """
    print("\n" + "="*60)
    print("NAVIGATION SYSTEM TEST")
    print("="*60)
    
    nav = Navigation()
    
    # Initialize
    if not nav.initialize():
        print("Initialization failed!")
        return
    
    # Option 1: Set destination from GPS
    print("\nOptions:")
    print("1. Acquire destination from GPS")
    print("2. Set manual destination (10m North of current)")
    choice = input("Choose (1/2): ").strip()
    
    if choice == "1":
        if not nav.set_destination():
            print("Failed to set destination!")
            return
    else:
        # Set destination 10m North for testing
        dest = {
            'lat': nav.p_current['lat'] + (10.0 / 111000.0),  # 10m North
            'lon': nav.p_current['lon'],
            'error': 0.0
        }
        nav.set_destination(dest)
    
    # Start navigation
    nav.start_navigation()
    
    # Main navigation loop
    dt = 1.0 / IMU_FREQUENCY
    
    try:
        while nav.navigation_active:
            status = nav.update(dt)
            
            if status and status['arrived']:
                break
            
            time.sleep(dt)
            
    except KeyboardInterrupt:
        print("\n\nNavigation interrupted by user")
        nav.stop_navigation()
    
    # Final summary
    print("\n" + "="*60)
    print("NAVIGATION TEST COMPLETE")
    print("="*60)
    summary = nav.get_status_summary()
    print(f"Final position: {summary['position_traveled']}")
    print(f"Distance to destination: {summary['distance_to_destination']:.2f}m")
    print(f"GPS recalibrations: {summary['gps_recalibrations']}")
    print(f"Total time: {summary['elapsed_time']:.1f}s")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_navigation()
