import math
import time
import numpy as np
from bmm150 import BMM150
from config import (
    MAG_DECLINATION,
    MAG_INTERFERENCE_THRESHOLD,
    MAG_FREQUENCY
)

_mag = None
_mag_offset = np.array([0.0, 0.0, 0.0])  # Hard iron calibration offset
_mag_scale = np.array([1.0, 1.0, 1.0])   # Soft iron calibration scale
_heading_history = []  # For smoothing
_last_heading = 0.0


def init_mag():
    """
    Initialize the BMM150 magnetometer.
    Returns True if successful.
    """
    global _mag
    
    if _mag is None:
        try:
            _mag = BMM150()
            print("BMM150 magnetometer initialized")
            return True
        except Exception as e:
            print(f"Magnetometer initialization failed: {e}")
            return False
    return True


def read_mag_raw():
    """
    Returns raw magnetometer values (mx, my, mz) in µT
    Returns: (mx, my, mz)
    """
    if _mag is None:
        init_mag()
    
    mx, my, mz = _mag.read_mag_data()
    return mx, my, mz


def read_mag_calibrated():
    """
    Returns calibrated magnetometer values with hard/soft iron correction.
    Returns: np.array([mx, my, mz]) in µT
    """
    mx, my, mz = read_mag_raw()
    mag = np.array([mx, my, mz])
    
    # Apply hard iron offset correction
    mag -= _mag_offset
    
    # Apply soft iron scale correction
    mag *= _mag_scale
    
    return mag


def get_heading(use_declination=True, smooth=True):
    """
    Calculate heading from magnetometer with corrections.
    
    Args:
        use_declination: Apply magnetic declination correction
        smooth: Apply moving average filter for stability
    
    Returns:
        Heading in degrees (0-360, 0=North)
    """
    global _last_heading, _heading_history
    
    mag = read_mag_calibrated()
    mx, my, mz = mag[0], mag[1], mag[2]
    
    # Calculate heading (NOT tilt-compensated, as you specified)
    # atan2(my, mx) gives angle in radians from magnetic North
    heading_rad = math.atan2(my, mx)
    heading = math.degrees(heading_rad)
    
    # Normalize to 0-360
    if heading < 0:
        heading += 360
    
    # Apply magnetic declination correction
    if use_declination:
        heading += MAG_DECLINATION
        if heading >= 360:
            heading -= 360
        elif heading < 0:
            heading += 360
    
    # Smooth heading with moving average (reduces jitter)
    if smooth:
        _heading_history.append(heading)
        if len(_heading_history) > 5:  # Average last 5 readings
            _heading_history.pop(0)
        
        # Handle wrap-around at 0/360 boundary
        heading = _average_angles(_heading_history)
    
    _last_heading = heading
    return heading


def get_heading_radians(use_declination=True, smooth=True):
    """
    Returns heading in radians (0 to 2π)
    """
    heading_deg = get_heading(use_declination, smooth)
    return math.radians(heading_deg)


def detect_interference():
    """
    Detect magnetic interference by checking field magnitude.
    Earth's magnetic field is typically 25-65 µT.
    
    Returns:
        True if interference detected, False otherwise
    """
    mag = read_mag_calibrated()
    magnitude = np.linalg.norm(mag)
    
    # Check if magnitude is abnormally high (interference)
    if magnitude > MAG_INTERFERENCE_THRESHOLD:
        print(f"WARNING: Magnetic interference detected! Magnitude: {magnitude:.1f} µT")
        return True
    
    # Check if magnitude is abnormally low (sensor issue or metal nearby)
    if magnitude < 20.0:
        print(f"WARNING: Weak magnetic field! Magnitude: {magnitude:.1f} µT")
        return True
    
    return False


def calibrate(duration=30, samples_per_second=10):
    """
    Calibrate magnetometer by rotating device through all orientations.
    Calculates hard iron offset and soft iron scale factors.
    
    IMPORTANT: Rotate the device slowly through ALL orientations during calibration:
    - Rotate around all 3 axes
    - Move in figure-8 patterns
    - Keep away from magnetic interference
    
    Args:
        duration: Calibration time in seconds (30s minimum recommended)
        samples_per_second: Sampling rate
    
    Returns:
        dict with 'offset' and 'scale' calibration values
    """
    global _mag_offset, _mag_scale
    
    print(f"\n{'='*60}")
    print("MAGNETOMETER CALIBRATION")
    print(f"{'='*60}")
    print(f"Duration: {duration} seconds")
    print("\nINSTRUCTIONS:")
    print("1. Move AWAY from metal objects, motors, and electronics")
    print("2. Rotate device slowly through ALL orientations")
    print("3. Make figure-8 patterns in the air")
    print("4. Ensure all axes are rotated equally")
    print(f"\nStarting in 3 seconds...")
    time.sleep(3)
    print("CALIBRATING NOW - START MOVING!\n")
    
    if _mag is None:
        init_mag()
    
    readings = []
    samples = duration * samples_per_second
    dt = 1.0 / samples_per_second
    
    for i in range(samples):
        mx, my, mz = read_mag_raw()
        readings.append([mx, my, mz])
        
        if (i + 1) % (samples // 10) == 0:
            progress = int((i + 1) / samples * 100)
            print(f"  Progress: {progress}% ({i+1}/{samples} samples)")
        
        time.sleep(dt)
    
    readings = np.array(readings)
    
    # Calculate hard iron offset (center of sphere)
    max_vals = np.max(readings, axis=0)
    min_vals = np.min(readings, axis=0)
    offset = (max_vals + min_vals) / 2.0
    
    # Calculate soft iron scale (normalize to sphere)
    ranges = max_vals - min_vals
    avg_range = np.mean(ranges)
    scale = avg_range / ranges
    
    _mag_offset = offset
    _mag_scale = scale
    
    print(f"\n{'='*60}")
    print("CALIBRATION COMPLETE!")
    print(f"{'='*60}")
    print(f"Hard iron offset: {offset}")
    print(f"Soft iron scale:  {scale}")
    print(f"\nAdd these to config.py:")
    print(f"MAG_OFFSET = {offset.tolist()}")
    print(f"MAG_SCALE = {scale.tolist()}")
    print(f"{'='*60}\n")
    
    return {
        'offset': offset,
        'scale': scale,
        'max_vals': max_vals,
        'min_vals': min_vals
    }


def load_calibration(offset, scale):
    """
    Load previously saved calibration values.
    
    Args:
        offset: Hard iron offset [mx_off, my_off, mz_off]
        scale: Soft iron scale [mx_scale, my_scale, mz_scale]
    """
    global _mag_offset, _mag_scale
    _mag_offset = np.array(offset)
    _mag_scale = np.array(scale)
    print(f"Loaded magnetometer calibration: offset={offset}, scale={scale}")


def _average_angles(angles):
    """
    Average angles handling wrap-around at 0/360 boundary.
    Uses circular mean.
    """
    angles_rad = [math.radians(a) for a in angles]
    sin_sum = sum(math.sin(a) for a in angles_rad)
    cos_sum = sum(math.cos(a) for a in angles_rad)
    
    avg_rad = math.atan2(sin_sum, cos_sum)
    avg_deg = math.degrees(avg_rad)
    
    if avg_deg < 0:
        avg_deg += 360
    
    return avg_deg


def get_heading_basic():
    """
    Simple heading without calibration or smoothing.
    (Legacy function for backward compatibility)
    """
    mx, my, mz = read_mag_raw()
    
    heading = math.degrees(math.atan2(my, mx))
    if heading < 0:
        heading += 360
    
    return heading


# ===== TEST MODES =====

def test_raw_readings(duration=10):
    """Test mode: Display raw magnetometer readings"""
    print("=== Testing Raw Magnetometer Readings ===")
    print("Earth's magnetic field is typically 25-65 µT\n")
    
    init_mag()
    
    start_time = time.time()
    try:
        while (time.time() - start_time) < duration:
            mx, my, mz = read_mag_raw()
            magnitude = math.sqrt(mx**2 + my**2 + mz**2)
            
            print(f"Mag: [{mx:7.2f}, {my:7.2f}, {mz:7.2f}] µT | "
                  f"Magnitude: {magnitude:6.2f} µT")
            
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    
    print("\nRaw readings test complete")


def test_heading(duration=10):
    """Test mode: Display heading with and without calibration"""
    print("=== Testing Magnetometer Heading ===")
    print("Rotate device to see heading changes\n")
    
    init_mag()
    
    start_time = time.time()
    try:
        while (time.time() - start_time) < duration:
            heading_raw = get_heading_basic()
            heading_cal = get_heading()
            
            interference = detect_interference()
            warning = " ⚠️  INTERFERENCE!" if interference else ""
            
            print(f"Heading (raw): {heading_raw:6.1f}° | "
                  f"Heading (calibrated): {heading_cal:6.1f}°{warning}")
            
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    
    print("\nHeading test complete")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "calibrate":
        # Run calibration
        calibrate(duration=30)
    
    elif len(sys.argv) > 1 and sys.argv[1] == "heading":
        # Test heading
        test_heading(duration=20)
    
    else:
        # Default: raw readings
        test_raw_readings(duration=10)
    
    print("\nUsage:")
    print("  python magnetometer.py              # Test raw readings")
    print("  python magnetometer.py calibrate    # Calibrate magnetometer")
    print("  python magnetometer.py heading      # Test heading output")