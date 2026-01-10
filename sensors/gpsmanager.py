# gps_manager.py
"""
GPS management - handles both IP geolocation and real GPS module.
Provides consistent interface regardless of source.
"""
import math
import config
from iplocation import get_location

# For real GPS module (uncomment when available)
# import serial
# import pynmea2

_gps_serial = None

def init_gps():
    """Initialize GPS - either IP geo or real module based on config."""
    global _gps_serial
    
    if config.USE_IP_GEOLOCATION:
        print("Using IP Geolocation for position")
        return True
    
    # Uncomment when real GPS available
    # try:
    #     _gps_serial = serial.Serial(config.GPS_SERIAL_PORT, 
    #                                  config.GPS_BAUD_RATE, 
    #                                  timeout=1)
    #     print("Real GPS module initialized")
    #     return True
    # except Exception as e:
    #     print(f"GPS init failed: {e}")
    #     return False

def get_position():
    """
    Returns current position as (lat, lon) tuple.
    Uses IP geo or real GPS based on config.
    """
    if config.USE_IP_GEOLOCATION:
        lat, lon = get_location()
        return lat, lon
    
    # Uncomment when real GPS available
    # try:
    #     line = _gps_serial.readline().decode('ascii', errors='replace')
    #     if line.startswith('$GPGGA') or line.startswith('$GPRMC'):
    #         msg = pynmea2.parse(line)
    #         return msg.latitude, msg.longitude
    # except Exception as e:
    #     print(f"GPS read error: {e}")
    #     return None, None
    
    return None, None

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two lat/lon points in meters.
    Uses Haversine formula.
    """
    R = 6371000  # Earth radius in meters
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    """
    Calculate initial bearing from point 1 to point 2 (degrees, 0-360).
    0° = North, 90° = East, 180° = South, 270° = West
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)
    
    y = math.sin(dlambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - \
        math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360) % 360

# Test mode
if __name__ == "__main__":
    init_gps()
    lat, lon = get_position()
    print(f"Current position: {lat}, {lon}")
    
    # Test distance/bearing calculation
    dest_lat, dest_lon = lat + 0.001, lon + 0.001  # ~100m northeast
    dist = haversine_distance(lat, lon, dest_lat, dest_lon)
    bearing = calculate_bearing(lat, lon, dest_lat, dest_lon)
    print(f"Distance to test point: {dist:.2f}m, Bearing: {bearing:.1f}°")