# gps_manager.py
"""
GPS management - handles IP geolocation, gpsd, or raw serial GPS.
Provides consistent interface regardless of source.
"""
import math
import config
from iplocation import get_location

# For gpsd
_gpsd_connected = False
if not config.USE_IP_GEOLOCATION:
    try:
        import gpsd
    except ImportError:
        print("Warning: gpsd-py3 not installed. Run: pip3 install gpsd-py3")

def init_gps():
    """Initialize GPS - either IP geo or gpsd based on config."""
    global _gpsd_connected
    
    if config.USE_IP_GEOLOCATION:
        print("Using IP Geolocation for position")
        return True
    
    if config.USE_GPSD:
        try:
            gpsd.connect()
            _gpsd_connected = True
            print("GPS (gpsd) initialized")
            return True
        except Exception as e:
            print(f"GPS init failed: {e}")
            print("Make sure gpsd is running: sudo systemctl status gpsd")
            return False
    
    return False

def get_position():
    """
    Returns current position as (lat, lon) tuple.
    Uses IP geo or gpsd based on config.
    """
    if config.USE_IP_GEOLOCATION:
        lat, lon = get_location()
        return lat, lon
    
    if config.USE_GPSD and _gpsd_connected:
        try:
            packet = gpsd.get_current()
            
            # Check for valid fix (mode 2 = 2D fix, mode 3 = 3D fix)
            has_fix = (
                packet.mode >= 2 and
                not math.isnan(packet.lat) and
                not math.isnan(packet.lon)
            )
            
            if has_fix:
                return packet.lat, packet.lon
            else:
                if config.DEBUG_PRINT_SENSORS:
                    print("Waiting for GPS fix...")
                return None, None
                
        except Exception as e:
            print(f"GPS read error: {e}")
            return None, None
    
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
    print("Testing GPS connection...")
    
    if init_gps():
        print("Waiting for GPS fix (this may take 30-60 seconds outdoors)...")
        
        attempts = 0
        max_attempts = 60
        
        while attempts < max_attempts:
            lat, lon = get_position()
            
            if lat is not None and lon is not None:
                print(f"\nGPS Fix acquired!")
                print(f"Current position: {lat:.6f}, {lon:.6f}")
                
                # Test distance/bearing calculation
                dest_lat, dest_lon = lat + 0.0001, lon + 0.0001  # ~15m northeast
                dist = haversine_distance(lat, lon, dest_lat, dest_lon)
                bearing = calculate_bearing(lat, lon, dest_lat, dest_lon)
                print(f"Distance to test point: {dist:.2f}m, Bearing: {bearing:.1f}°")
                break
            else:
                print(f"Attempt {attempts+1}/{max_attempts}: No fix yet...")
                attempts += 1
                
            import time
            time.sleep(1)
        
        if attempts >= max_attempts:
            print("\nFailed to get GPS fix. Make sure:")
            print("- GPS antenna has clear view of sky")
            print("- gpsd is running: sudo systemctl status gpsd")
            print("- GPS device is configured in /etc/default/gpsd")
    else:
        print("GPS initialization failed!")