# coordinate_transform.py

import math
import config

# Reference point for local coordinate system
_ref_lat = None
_ref_lon = None

def set_reference_point(lat, lon):
    
    if lat is None or lon is None:
        raise ValueError("Cannot set reference point: GPS fix not available")
        
    global _ref_lat, _ref_lon
    _ref_lat = lat
    _ref_lon = lon
    config.REF_LAT = lat
    config.REF_LON = lon
    print(f"Reference point: {lat:.6f}, {lon:.6f}")

def latlon_to_xy(lat, lon):
    
    if _ref_lat is None:
        raise ValueError("Call set_reference_point() first")
    
    # Meters per degree
    lat_m_per_deg = 110540  # ~constant everywhere
    lon_m_per_deg = 111320 * math.cos(math.radians(_ref_lat))
    
    x = (lon - _ref_lon) * lon_m_per_deg  # East (+) / West (-)
    y = (lat - _ref_lat) * lat_m_per_deg  # North (+) / South (-)
    
    return x, y

def xy_to_latlon(x, y):
    
    if _ref_lat is None:
        raise ValueError("Reference point not set")
    
    lat_m_per_deg = 110540
    lon_m_per_deg = 111320 * math.cos(math.radians(_ref_lat))
    
    lat = _ref_lat + (y / lat_m_per_deg)
    lon = _ref_lon + (x / lon_m_per_deg)
    
    return lat, lon

def body_to_earth_frame(ax_body, ay_body, heading_deg):
    
    heading_rad = math.radians(heading_deg)
    
    # Rotation matrix
    ax_earth = ax_body * math.sin(heading_rad) + ay_body * math.cos(heading_rad)
    ay_earth = ax_body * math.cos(heading_rad) - ay_body * math.sin(heading_rad)
    
    return ax_earth, ay_earth

def normalize_angle(angle):
    """Normalize angle to 0-360 range."""
    return angle % 360

def angle_difference(target, current):
    
    diff = target - current
    # Normalize to -180 to +180
    while diff > 180:
        diff -= 360
    while diff < -180:
        diff += 360
    return diff

def distance_2d(x1, y1, x2, y2):
    
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def bearing_to_point(x1, y1, x2, y2):
    
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