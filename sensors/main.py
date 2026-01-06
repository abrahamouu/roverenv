# main.py
"""
Main entry point for the IMU/Magnetometer-based navigation system.
Integrates sensor fusion navigation with motor control.

Algorithm:
    D_relative = P_destination - P_current (GPS waypoints)
    D_traveled = IMU + Magnetometer fusion (high-frequency)
    Error check: |D_traveled - D_relative| < epsilon
"""

import time
import sys
import math
from navigation import Navigation
from config import IMU_FREQUENCY, ENABLE_DEBUG_LOGGING, POSITION_EPSILON
from motor_helper import forward, backward, turn_left, turn_right, stop


def heading_error(target, current):
    """
    Calculate heading error (shortest angular distance).
    Returns value between -180 and 180 degrees.
    """
    error = (target - current + 540) % 360 - 180
    return error


def motor_control_loop(nav):
    """
    Main motor control loop - integrates navigation with motor commands.
    
    Args:
        nav: Navigation object
    
    Returns:
        True if destination reached, False if stopped
    """
    dt = 1.0 / IMU_FREQUENCY
    last_status_time = time.time()
    
    # Tunable parameters for motor control
    HEADING_ERROR_LARGE = 25.0  # degrees - rotate in place
    HEADING_ERROR_SMALL = 10.0  # degrees - gentle correction
    FORWARD_SPEED = 0.5         # speed when going straight
    TURN_SPEED = 0.3            # speed when turning
    
    print("\n[NAVIGATING...]")
    print("Press Ctrl+C to stop\n")
    print("-" * 70)
    
    try:
        while nav.navigation_active:
            # Get navigation update
            status = nav.update(dt)
            
            if status is None:
                time.sleep(dt)
                continue
            
            # Check if arrived
            if status['arrived']:
                stop()
                print("\n" + "="*70)
                print("SUCCESS! DESTINATION REACHED!")
                print("="*70)
                return True
            
            # Get current heading and target bearing
            current_heading = status['heading']
            target_bearing = status['bearing_to_dest']
            distance_remaining = status['destination_distance']
            
            # Calculate heading error
            error = heading_error(target_bearing, current_heading)
            
            # Motor control logic based on heading error
            if abs(error) > HEADING_ERROR_LARGE:
                # Large error: rotate in place
                if error > 0:
                    turn_right(TURN_SPEED)
                    action = "Turning RIGHT (large correction)"
                else:
                    turn_left(TURN_SPEED)
                    action = "Turning LEFT (large correction)"
            
            elif abs(error) > HEADING_ERROR_SMALL:
                # Medium error: gentle turn while moving
                if error > 0:
                    turn_right(TURN_SPEED * 0.7)
                    action = "Turning right (gentle)"
                else:
                    turn_left(TURN_SPEED * 0.7)
                    action = "Turning left (gentle)"
            
            else:
                # Small error: move forward
                forward(FORWARD_SPEED)
                action = "Moving forward"
            
            # Display status every second (unless debug logging is on)
            if not ENABLE_DEBUG_LOGGING:
                current_time = time.time()
                if (current_time - last_status_time) >= 1.0:
                    print(f"[{status['elapsed_time']:6.1f}s] "
                          f"Dist: {distance_remaining:5.1f}m | "
                          f"Head: {current_heading:5.1f}° | "
                          f"Target: {target_bearing:5.1f}° | "
                          f"Error: {error:+5.1f}° | "
                          f"{action}")
                    last_status_time = current_time
            
            time.sleep(dt)
    
    except KeyboardInterrupt:
        print("\n\nNavigation interrupted by user")
        stop()
        nav.stop_navigation()
        return False
    
    return True


def print_final_summary(nav, success):
    """
    Print final navigation summary.
    """
    summary = nav.get_status_summary()
    
    print("\n" + "="*70)
    print("NAVIGATION SUMMARY")
    print("="*70)
    
    if success:
        print("Status: DESTINATION REACHED")
    else:
        print("Status: NAVIGATION STOPPED")
    
    print(f"\nStarting Position:")
    print(f"  Lat: {nav.p_current['lat']:.6f}")
    print(f"  Lon: {nav.p_current['lon']:.6f}")
    
    print(f"\nDestination:")
    print(f"  Lat: {nav.p_destination['lat']:.6f}")
    print(f"  Lon: {nav.p_destination['lon']:.6f}")
    
    print(f"\nNavigation Stats:")
    print(f"  Planned Distance: {nav.d_relative_magnitude:.1f} meters")
    
    if summary['distance_to_destination'] is not None:
        print(f"  Distance Remaining: {summary['distance_to_destination']:.1f} meters")
        print(f"  Final Error: {summary['distance_to_destination']:.2f}m (threshold: {POSITION_EPSILON}m)")
    
    print(f"  GPS Recalibrations: {summary['gps_recalibrations']}")
    print(f"  Total Time: {summary['elapsed_time']:.1f} seconds")
    
    print("="*70 + "\n")


def main():
    """
    Main program flow.
    """
    print("\n" + "="*70)
    print("  IMU/MAGNETOMETER NAVIGATION SYSTEM")
    print("  UGV Autonomous Navigation to GPS Coordinates")
    print("="*70)
    
    # Create navigation system
    nav = Navigation()
    
    # Step 1: Initialize all sensors
    print("\n[STEP 1] Initializing sensors...")
    if not nav.initialize():
        print("\nINITIALIZATION FAILED!")
        print("\nTroubleshooting:")
        print("  - GPS: Check if gpsd is running (sudo systemctl status gpsd)")
        print("  - IMU: Check I2C connection (i2cdetect -y 1, should see 0x68)")
        print("  - Magnetometer: Check I2C connection (should see 0x13 or 0x10)")
        return 1
    
    print("All sensors initialized successfully!")
    print(f" Current Position: ({nav.p_current['lat']:.6f}, {nav.p_current['lon']:.6f})")
    
    # Step 2: Get destination coordinates
    print("\n[STEP 2] Enter Destination Coordinates")
    print("-" * 70)
    
    try:
        dest_lat = float(input("Enter destination latitude (e.g., 34.123456): "))
        dest_lon = float(input("Enter destination longitude (e.g., -118.123456): "))
    except (ValueError, KeyboardInterrupt):
        print("\n Invalid coordinates!")
        return 1
    
    # Create destination dict
    destination = {
        'lat': dest_lat,
        'lon': dest_lon,
        'error': 0.0
    }
    
    # Set destination
    if not nav.set_destination(destination):
        print(" Failed to set destination!")
        return 1
    
    # Step 3: Confirm navigation parameters
    print("\n[STEP 3] Navigation Plan")
    print("-" * 70)
    print(f" Current:     ({nav.p_current['lat']:.6f}, {nav.p_current['lon']:.6f})")
    print(f" Destination: ({nav.p_destination['lat']:.6f}, {nav.p_destination['lon']:.6f})")
    print(f" Distance:    {nav.d_relative_magnitude:.1f} meters")
    print(f" Bearing:     {nav._calculate_bearing():.1f}°")
    print("-" * 70)
    
    # Sanity check on distance
    if nav.d_relative_magnitude > 1000:
        print(f"\n  WARNING: Distance is {nav.d_relative_magnitude:.0f}m (>1km)")
        confirm = input("This is a long distance. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Navigation cancelled.")
            return 0
    
    try:
        input("\nPress Enter to start navigation (Ctrl+C to cancel)...")
    except KeyboardInterrupt:
        print("\n\nNavigation cancelled.")
        return 0
    
    # Start navigation
    nav.start_navigation()
    
    # Step 4: Run motor control loop
    success = motor_control_loop(nav)
    
    # Step 5: Final summary
    print_final_summary(nav, success)
    
    # Ensure motors are stopped
    stop()
    
    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        stop()  # Ensure motors stop on error
        sys.exit(1)