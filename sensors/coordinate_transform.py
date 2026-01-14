# coordinate_transform.py
"""
Coordinate transformations for navigation:
- Lat/Lon <-> Local XY meters (flat Earth approximation)
- Body frame <-> Earth frame rotations (for IMU acceleration)
"""
import math
import config

# Reference point for local coordinate system
_ref_lat = None
_ref_lon = None

def set_reference_point(lat, lon):
    """
    Set origin of local Cartesian coordinate system.
    Call once at startup with initial GPS position.
    """
    global _ref_lat, _ref_lon
    _ref_lat = lat
    _ref_lon = lon
    config.REF_LAT = lat
    config.REF_LON = lon
    print(f"Reference point: {lat:.6f}, {lon:.6f}")

def latlon_to_xy(lat, lon):
    """
    Convert GPS lat/lon to local XY meters.
    Returns: (x_east, y_north) in meters from reference point
    """
    if _ref_lat is None:
        raise ValueError("Call set_reference_point() first")
    
    # Meters per degree
    lat_m_per_deg = 110540  # ~constant everywhere
    lon_m_per_deg = 111320 * math.cos(math.radians(_ref_lat))
    
    x = (lon - _ref_lon) * lon_m_per_deg  # East (+) / West (-)
    y = (lat - _ref_lat) * lat_m_per_deg  # North (+) / South (-)
    
    return x, y

def xy_to_latlon(x, y):
    """
    Convert local XY meters back to lat/lon.
    Useful for displaying position on map.
    """
    if _ref_lat is None:
        raise ValueError("Reference point not set")
    
    lat_m_per_deg = 110540
    lon_m_per_deg = 111320 * math.cos(math.radians(_ref_lat))
    
    lat = _ref_lat + (y / lat_m_per_deg)
    lon = _ref_lon + (x / lon_m_per_deg)
    
    return lat, lon

def body_to_earth_frame(ax_body, ay_body, heading_deg):
    """
    Rotate acceleration from body frame to earth frame.
    
    Body frame: x=forward, y=left (from rover's perspective)
    Earth frame: x=East, y=North (fixed to ground)
    
    Args:
        ax_body: forward acceleration (m/s²)
        ay_body: left acceleration (m/s²)  
        heading_deg: rover heading from magnetometer (0°=North)
    
    Returns:
        (ax_east, ay_north) in earth frame
    """
    heading_rad = math.radians(heading_deg)
    
    # Rotation matrix
    ax_earth = ax_body * math.sin(heading_rad) + ay_body * math.cos(heading_rad)
    ay_earth = ax_body * math.cos(heading_rad) - ay_body * math.sin(heading_rad)
    
    return ax_earth, ay_earth

def normalize_angle(angle):
    """Normalize angle to 0-360 range."""
    return angle % 360

def angle_difference(target, current):
    """
    Calculate shortest angular difference (target - current).
    Returns: -180 to +180 degrees
        Positive = turn right
        Negative = turn left
    """
    diff = target - current
    # Normalize to -180 to +180
    while diff > 180:
        diff -= 360
    while diff < -180:
        diff += 360
    return diff

def distance_2d(x1, y1, x2, y2):
    """Euclidean distance between two XY points."""
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def bearing_to_point(x1, y1, x2, y2):
    """
    Calculate bearing from point 1 to point 2.
    Returns: 0-360° where 0°=North, 90°=East
    """
    dx = x2 - x1
    dy = y2 - y1
    bearing = math.degrees(math.atan2(dx, dy))
    return normalize_angle(bearing)

# Test mode
if __name__ == "__main__":
    # Test coordinate conversion
    set_reference_point(33.7015, -117.7528)
    
    # Test: 50m North, 30m East
    x, y = 30, 50
    lat, lon = xy_to_latlon(x, y)
    print(f"XY ({x}, {y}) -> Lat/Lon ({lat:.6f}, {lon:.6f})")
    
    # Convert back
    x2, y2 = latlon_to_xy(lat, lon)
    print(f"Round trip: ({x2:.2f}, {y2:.2f}) - Error: {abs(x-x2):.4f}m")
    
    # Test body->earth frame rotation
    print("\nBody->Earth frame tests:")
    test_cases = [
        (1.0, 0.0, 0),    # Moving forward, heading North
        (1.0, 0.0, 90),   # Moving forward, heading East
        (0.0, 1.0, 0),    # Moving left, heading North
    ]
    
    for ax_body, ay_body, heading in test_cases:
        ax_earth, ay_earth = body_to_earth_frame(ax_body, ay_body, heading)
        print(f"Body({ax_body}, {ay_body}) @ {heading}° -> Earth({ax_earth:.2f}, {ay_earth:.2f})")
    
    # Test angle difference
    print("\nAngle difference tests:")
    print(f"Target 90°, Current 80° -> {angle_difference(90, 80):.0f}° (turn right)")
    print(f"Target 10°, Current 350° -> {angle_difference(10, 350):.0f}° (turn right)")
    print(f"Target 350°, Current 10° -> {angle_difference(350, 10):.0f}° (turn left)")