# sensor_fusion.py
import time
import math
import numpy as np
from config import (
    IMU_FREQUENCY,
    MAG_FREQUENCY,
    HEADING_CORRECTION_ENABLED,
    IMU_FORWARD_AXIS,
    IMU_RIGHT_AXIS,
    ENABLE_DEBUG_LOGGING
)
import imu
import magnetometer

# State variables
_reference_position = np.array([0.0, 0.0])  # GPS reference point (lat, lon) or (x, y)
_fused_position = np.array([0.0, 0.0])  # Current fused position (x, y) in meters
_reference_heading = 0.0  # Initial heading when reference was set
_last_mag_update = 0.0
_mag_update_interval = 1.0 / MAG_FREQUENCY


def init_fusion():
    """
    Initialize sensor fusion system.
    Must be called before using fusion functions.
    
    Returns:
        True if all sensors initialized successfully
    """
    print("Initializing sensor fusion system...")
    
    imu_ok = imu.init_imu()
    mag_ok = magnetometer.init_mag()
    
    if not (imu_ok and mag_ok):
        print("Sensor fusion initialization failed!")
        return False
    
    print("Sensor fusion initialized successfully")
    return True


def set_reference_point(gps_position=None, heading=None):
    """
    Set the reference point for relative navigation.
    Call this when you have a GPS fix or at waypoints.
    
    Args:
        gps_position: GPS coordinates as dict {'lat': lat, 'lon': lon} or None
        heading: Initial heading in degrees (if None, reads from magnetometer)
    
    This resets IMU integration and establishes new origin for relative positioning.
    """
    global _reference_position, _fused_position, _reference_heading
    
    # Reset IMU integration (zeros velocity and position)
    imu.reset_integration()
    
    # Reset fused position to origin
    _fused_position = np.array([0.0, 0.0])
    
    # Store GPS reference (if provided)
    if gps_position:
        _reference_position = np.array([gps_position['lat'], gps_position['lon']])
        print(f"Reference point set: ({gps_position['lat']:.6f}, {gps_position['lon']:.6f})")
    
    # Store or read reference heading
    if heading is not None:
        _reference_heading = heading
    else:
        _reference_heading = magnetometer.get_heading()
    
    print(f"Reference heading: {_reference_heading:.1f}°")


def update(dt=None):
    """
    Main sensor fusion update - call this at IMU_FREQUENCY Hz.
    
    This function:
    1. Gets IMU displacement (double integrated acceleration)
    2. Gets magnetometer heading (periodically)
    3. Rotates IMU displacement by heading to correct drift
    4. Returns fused position estimate
    
    Args:
        dt: Time delta in seconds (if None, calculated automatically)
    
    Returns:
        dict with fused position and metadata
    """
    global _fused_position, _last_mag_update
    
    current_time = time.time()
    
    # Step 1: Get IMU displacement (this has drift in heading)
    imu_result = imu.integrate_step(dt)
    imu_displacement_3d = imu_result['position']  # [dx, dy, dz] in IMU frame
    
    # Extract 2D displacement (forward, right) - ignore vertical
    imu_displacement_2d = np.array([
        imu_displacement_3d[IMU_FORWARD_AXIS],
        imu_displacement_3d[IMU_RIGHT_AXIS]
    ])
    
    # Step 2: Get current heading from magnetometer (at MAG_FREQUENCY)
    if HEADING_CORRECTION_ENABLED and (current_time - _last_mag_update) >= _mag_update_interval:
        current_heading = magnetometer.get_heading()
        _last_mag_update = current_time
        
        # Check for magnetic interference
        if magnetometer.detect_interference():
            print("WARNING: Using IMU-only positioning due to magnetic interference")
            current_heading = _reference_heading  # Fall back to reference heading
    else:
        # Use last known heading (between magnetometer updates)
        current_heading = magnetometer._last_heading if hasattr(magnetometer, '_last_heading') else _reference_heading
    
    # Step 3: Calculate heading error (this is your theta correction)
    # heading_error = how much the device has rotated from reference
    heading_error = current_heading - _reference_heading
    
    # Step 4: Rotate IMU displacement by heading error
    # This corrects for the drift in heading angle (your +C drift term)
    corrected_displacement = apply_heading_correction(imu_displacement_2d, heading_error)
    
    # Step 5: Update fused position
    _fused_position = corrected_displacement
    
    # Return complete state
    return {
        'position': _fused_position.copy(),  # [x, y] in meters from reference
        'heading': current_heading,  # degrees
        'heading_error': heading_error,  # degrees of drift correction applied
        'imu_displacement': imu_displacement_2d.copy(),  # uncorrected
        'velocity': imu_result['velocity'][[IMU_FORWARD_AXIS, IMU_RIGHT_AXIS]],
        'timestamp': current_time
    }


def apply_heading_correction(displacement, heading_error_deg):
    """
    Apply rotation to IMU displacement based on heading error.
    
    This is the KEY function that implements your drift correction:
    - IMU gives displacement in its own (drifting) reference frame
    - Magnetometer gives true heading
    - We rotate the IMU displacement to align with true North
    
    Args:
        displacement: np.array([forward, right]) in IMU frame
        heading_error_deg: Heading error in degrees (theta correction)
    
    Returns:
        np.array([x, y]) corrected displacement in world frame
    """
    # Convert heading error to radians
    theta = math.radians(heading_error_deg)
    
    # Rotation matrix: rotates vector by theta
    # [x']   [cos(θ)  -sin(θ)] [x]
    # [y'] = [sin(θ)   cos(θ)] [y]
    cos_theta = math.cos(theta)
    sin_theta = math.sin(theta)
    
    rotation_matrix = np.array([
        [cos_theta, -sin_theta],
        [sin_theta,  cos_theta]
    ])
    
    # Apply rotation
    corrected = rotation_matrix @ displacement
    
    return corrected


def get_position():
    """
    Get current fused position estimate.
    
    Returns:
        np.array([x, y]) in meters from reference point
    """
    return _fused_position.copy()


def get_position_gps():
    """
    Convert current fused position to GPS coordinates.
    
    This is approximate (assumes flat earth for small distances).
    For more accuracy, use proper geodetic conversions.
    
    Returns:
        dict {'lat': lat, 'lon': lon} or None if no reference set
    """
    if _reference_position is None or np.all(_reference_position == 0):
        return None
    
    # Approximate conversion (meters to degrees)
    # At equator: 1° lat ≈ 111km, 1° lon ≈ 111km
    # At your latitude, lon scaling differs
    meters_per_degree_lat = 111000.0
    meters_per_degree_lon = 111000.0 * math.cos(math.radians(_reference_position[0]))
    
    delta_lat = _fused_position[1] / meters_per_degree_lat  # y = North
    delta_lon = _fused_position[0] / meters_per_degree_lon  # x = East
    
    current_lat = _reference_position[0] + delta_lat
    current_lon = _reference_position[1] + delta_lon
    
    return {
        'lat': current_lat,
        'lon': current_lon
    }


def get_distance_from_reference():
    """
    Get straight-line distance from reference point.
    
    Returns:
        Distance in meters
    """
    return np.linalg.norm(_fused_position)


def recalibrate_from_gps(gps_position, reset_position=True):
    """
    Recalibrate fusion using GPS fix.
    
    This is called periodically (every GPS_RECHECK_INTERVAL) to correct
    for magnitude drift in IMU (the +Cx+D terms you can't correct with heading alone).
    
    Args:
        gps_position: GPS coordinates dict {'lat': lat, 'lon': lon}
        reset_position: If True, resets position to GPS (hard reset)
                       If False, adjusts for drift but maintains continuity
    """
    global _reference_position, _fused_position
    
    if reset_position:
        # Hard reset: treat GPS as new reference point
        set_reference_point(gps_position)
        print(f"GPS recalibration: Hard reset to ({gps_position['lat']:.6f}, {gps_position['lon']:.6f})")
    else:
        # Soft reset: calculate drift and adjust
        # Convert GPS to meters from current reference
        gps_position_meters = gps_to_meters(gps_position, _reference_position)
        
        # Calculate drift (difference between GPS and fused estimate)
        drift = gps_position_meters - _fused_position
        drift_magnitude = np.linalg.norm(drift)
        
        print(f"GPS recalibration: Drift detected = {drift_magnitude:.2f}m")
        
        # Update fused position to match GPS
        _fused_position = gps_position_meters.copy()
        
        # Optionally adjust IMU bias here based on drift
        # (advanced: not implemented in basic version)


def gps_to_meters(gps_position, reference_position):
    """
    Convert GPS coordinates to meters from reference point.
    
    Args:
        gps_position: dict {'lat': lat, 'lon': lon}
        reference_position: np.array([ref_lat, ref_lon])
    
    Returns:
        np.array([x, y]) in meters (East, North)
    """
    delta_lat = gps_position['lat'] - reference_position[0]
    delta_lon = gps_position['lon'] - reference_position[1]
    
    meters_per_degree_lat = 111000.0
    meters_per_degree_lon = 111000.0 * math.cos(math.radians(reference_position[0]))
    
    x = delta_lon * meters_per_degree_lon  # East
    y = delta_lat * meters_per_degree_lat  # North
    
    return np.array([x, y])


def get_status():
    """
    Get complete fusion status for logging/debugging.
    
    Returns:
        dict with all state variables
    """
    return {
        'fused_position': _fused_position.copy(),
        'reference_position': _reference_position.copy(),
        'reference_heading': _reference_heading,
        'distance_from_ref': get_distance_from_reference(),
        'gps_position': get_position_gps()
    }


# ===== TEST MODE =====

def test_fusion(duration=30):
    """
    Test sensor fusion by walking/moving in a straight line.
    Compare IMU-only vs fused (heading-corrected) position.
    """
    print("=== Testing Sensor Fusion ===")
    print(f"Duration: {duration} seconds")
    print("\nMove forward in a straight line...\n")
    
    init_fusion()
    set_reference_point()
    
    dt = 1.0 / IMU_FREQUENCY
    start_time = time.time()
    
    try:
        while (time.time() - start_time) < duration:
            result = update(dt)
            
            pos = result['position']
            heading = result['heading']
            heading_error = result['heading_error']
            
            if ENABLE_DEBUG_LOGGING and int(time.time() * 1) % 1 == 0:  # Print at LOG_FREQUENCY
                print(f"Pos: [{pos[0]:6.2f}, {pos[1]:6.2f}]m | "
                      f"Heading: {heading:6.1f}° | "
                      f"Correction: {heading_error:+5.1f}°")
            
            time.sleep(dt)
            
    except KeyboardInterrupt:
        pass
    
    final_pos = get_position()
    distance = get_distance_from_reference()
    
    print(f"\n{'='*60}")
    print("Test Complete!")
    print(f"Final position: [{final_pos[0]:.2f}, {final_pos[1]:.2f}] meters")
    print(f"Distance traveled: {distance:.2f} meters")
    print(f"{'='*60}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_fusion(duration=30)
    else:
        print("Sensor Fusion Module")
        print("\nUsage:")
        print("  python sensor_fusion.py test    # Test fusion system")
        print("\nThis module is meant to be imported by navigation.py")