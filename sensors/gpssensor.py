import gps
import time
from typing import Optional, Dict

session = None
gps_initialized = False

def init_gps(cold_start_timeout=60):
    """
    Initialize GPS with longer timeout for NEO-6M cold start.
    Returns True if successful.
    """
    global session, gps_initialized
    
    if gps_initialized and session is not None:
        return True
    
    try:
        print("Initializing NEO-6M GPS module...")
        session = gps.gps(mode=gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
        
        # Wait for first valid fix (NEO-6M cold start can take 30-60s)
        print(f"Waiting for GPS fix (timeout: {cold_start_timeout}s)...")
        start_time = time.time()
        
        while (time.time() - start_time) < cold_start_timeout:
            try:
                report = session.next()
                if report['class'] == 'TPV' and getattr(report, 'mode', 0) >= 2:
                    print(f"GPS fix acquired in {time.time() - start_time:.1f}s")
                    gps_initialized = True
                    return True
            except StopIteration:
                time.sleep(0.5)
            except Exception as e:
                print(f"Error during GPS init: {e}")
                
        print("GPS initialization timeout - no fix acquired")
        return False
        
    except Exception as e:
        print(f"GPS initialization failed: {e}")
        print("Check: 1) gpsd running? 2) Serial connection? 3) Antenna attached?")
        return False

def get_gps(timeout=3.0) -> Optional[Dict]:
    """
    Get GPS reading from NEO-6M with timeout.
    Returns dict with position, accuracy, and quality metrics.
    """
    if not gps_initialized:
        if not init_gps():
            return None
    
    start_time = time.time()
    
    while (time.time() - start_time) < timeout:
        try:
            report = session.next()
            
            if report['class'] == 'TPV':
                mode = getattr(report, 'mode', 0)
                # mode: 0=no fix, 1=no fix, 2=2D fix, 3=3D fix
                if mode < 2:
                    continue
                
                lat = getattr(report, 'lat', None)
                lon = getattr(report, 'lon', None)
                
                if lat is None or lon is None:
                    continue
                
                # NEO-6M specific accuracy metrics
                result = {
                    'lat': lat,
                    'lon': lon,
                    'altitude': getattr(report, 'alt', None),  # 3D fix only
                    'timestamp': getattr(report, 'time', time.time()),
                    'epx': getattr(report, 'epx', 2.5),  # Default ~2.5m for NEO-6M
                    'epy': getattr(report, 'epy', 2.5),
                    'mode': mode,
                    'satellites': getattr(report, 'sat', 0),  # Number of satellites
                }
                
                print(f"GPS: ({lat:.6f}, {lon:.6f}) | Sats: {result['satellites']} | Error: ±{max(result['epx'], result['epy']):.1f}m")
                return result
                
            elif report['class'] == 'SKY':
                # Optional: track satellite info for debugging
                sats = getattr(report, 'satellites', [])
                print(f"Tracking {len(sats)} satellites")
                
        except StopIteration:
            time.sleep(0.1)  # NEO-6M updates at 1Hz, so 100ms poll is fine
        except Exception as e:
            print(f"GPS read error: {e}")
            return None
    
    return None

def get_waypoint(name="waypoint", retries=3) -> Optional[Dict]:
    """
    Get a GPS waypoint with retries - use this for your initial/destination positions.
    Averages multiple readings for better accuracy.
    """
    print(f"Acquiring {name}...")
    readings = []
    
    for attempt in range(retries):
        gps_data = get_gps(timeout=5.0)
        if gps_data:
            readings.append(gps_data)
            print(f"  Reading {attempt+1}/{retries} acquired")
        else:
            print(f"  Reading {attempt+1}/{retries} failed")
    
    if not readings:
        print(f"Failed to acquire {name}")
        return None
    
    # Average the readings for better accuracy
    avg_lat = sum(r['lat'] for r in readings) / len(readings)
    avg_lon = sum(r['lon'] for r in readings) / len(readings)
    max_error = max(max(r['epx'], r['epy']) for r in readings)
    
    result = {
        'lat': avg_lat,
        'lon': avg_lon,
        'error': max_error,
        'samples': len(readings),
        'timestamp': readings[-1]['timestamp']
    }
    
    print(f"{name}: ({avg_lat:.6f}, {avg_lon:.6f}) ±{max_error:.1f}m from {len(readings)} samples")
    return result

def close_gps():
    """Clean shutdown"""
    global session, gps_initialized
    if session:
        session.close()
    session = None
    gps_initialized = False