import time
import numpy as np
from mpu6050 import mpu6050
from config import (
    IMU_FREQUENCY,
    ACCEL_BIAS,
    VELOCITY_DECAY,
    POSITION_DECAY,
    VELOCITY_RESET_THRESHOLD,
    IMU_FORWARD_AXIS,
    IMU_RIGHT_AXIS,
    IMU_DOWN_AXIS
)

_imu = None
_velocity = np.array([0.0, 0.0, 0.0])  # m/s
_position = np.array([0.0, 0.0, 0.0])  # m
_last_update_time = None
_accel_bias = np.array(ACCEL_BIAS)  # Calibrated bias


def init_imu(address=0x68):
    """
    Initialize the MPU6050 IMU.
    Creates the sensor once—safe to call multiple times.
    Returns True if successful.
    """
    global _imu, _last_update_time
    
    if _imu is None:
        try:
            _imu = mpu6050(address)
            _last_update_time = time.time()
            print("MPU6050 initialized successfully")
            return True
        except Exception as e:
            print(f"IMU initialization failed: {e}")
            return False
    return True


def get_accel_raw():
    """
    Returns raw accelerometer data in m/s² (before bias correction)
    Returns: (ax, ay, az)
    """
    if _imu is None:
        init_imu()
    
    data = _imu.get_accel_data()
    return data['x'], data['y'], data['z']


def get_accel():
    """
    Returns bias-corrected accelerometer data in m/s²
    Returns: np.array([ax, ay, az])
    """
    ax, ay, az = get_accel_raw()
    accel = np.array([ax, ay, az])
    
    # Subtract calibrated bias
    accel -= _accel_bias
    
    # Subtract gravity (assuming az is "down" axis)
    # If device is level, az should read ~9.81 m/s²
    # This removes static gravity component
    accel[IMU_DOWN_AXIS] -= 9.81
    
    return accel


def get_gyro():
    """
    Returns gyro data in deg/sec
    Returns: (gx, gy, gz)
    """
    if _imu is None:
        init_imu()
    
    data = _imu.get_gyro_data()
    return data['x'], data['y'], data['z']


def integrate_step(dt=None):
    """
    Perform one integration step: accel → velocity → position
    Call this at IMU_FREQUENCY Hz
    
    Args:
        dt: Time delta in seconds. If None, calculated from last call.
    
    Returns:
        dict with velocity and displacement
    """
    global _velocity, _position, _last_update_time
    
    # Calculate time delta
    current_time = time.time()
    if dt is None:
        if _last_update_time is None:
            _last_update_time = current_time
            return {'velocity': _velocity.copy(), 'position': _position.copy()}
        dt = current_time - _last_update_time
    _last_update_time = current_time
    
    # Get bias-corrected acceleration
    accel = get_accel()
    
    # === FIRST INTEGRATION: accel → velocity ===
    # v(t+dt) = v(t) + a*dt
    _velocity += accel * dt
    
    # Apply velocity decay to combat drift (exponential decay)
    _velocity *= VELOCITY_DECAY
    
    # Zero-velocity update: if stationary, force velocity to zero
    if np.linalg.norm(_velocity) < VELOCITY_RESET_THRESHOLD:
        _velocity = np.array([0.0, 0.0, 0.0])
    
    # === SECOND INTEGRATION: velocity → position ===
    # p(t+dt) = p(t) + v*dt
    _position += _velocity * dt
    
    # Apply position decay (optional, helps with long-term drift)
    _position *= POSITION_DECAY
    
    return {
        'velocity': _velocity.copy(),
        'position': _position.copy(),
        'accel': accel.copy(),
        'dt': dt
    }


def get_velocity():
    """
    Returns current velocity vector in m/s
    Returns: np.array([vx, vy, vz])
    """
    return _velocity.copy()


def get_position():
    """
    Returns current position (displacement from reset point) in meters
    Returns: np.array([dx, dy, dz])
    """
    return _position.copy()


def get_displacement_2d():
    """
    Returns 2D horizontal displacement (ignoring vertical)
    Useful for ground navigation
    Returns: np.array([dx, dy]) in meters
    """
    return _position[[IMU_FORWARD_AXIS, IMU_RIGHT_AXIS]].copy()


def reset_integration():
    """
    Zero out velocity and position.
    Call this when GPS recalibrates or at waypoints.
    """
    global _velocity, _position, _last_update_time
    _velocity = np.array([0.0, 0.0, 0.0])
    _position = np.array([0.0, 0.0, 0.0])
    _last_update_time = time.time()
    print("IMU integration reset")


def calibrate_bias(samples=100, duration=5.0):
    """
    Calibrate accelerometer bias by averaging readings while stationary.
    Device MUST be stationary and level during calibration.
    
    Args:
        samples: Number of samples to average
        duration: Time in seconds to collect samples
    
    Returns:
        np.array([bias_x, bias_y, bias_z])
    """
    global _accel_bias
    
    print(f"Calibrating IMU bias... Keep device STATIONARY for {duration}s")
    
    if _imu is None:
        init_imu()
    
    readings = []
    dt = duration / samples
    
    for i in range(samples):
        ax, ay, az = get_accel_raw()
        readings.append([ax, ay, az])
        time.sleep(dt)
        
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{samples} samples...")
    
    # Calculate mean (this is the bias)
    readings = np.array(readings)
    bias = np.mean(readings, axis=0)
    
    # Subtract gravity from the "down" axis bias
    # (We want to measure bias, not gravity)
    bias[IMU_DOWN_AXIS] -= 9.81
    
    _accel_bias = bias
    print(f"Calibration complete: bias = {bias}")
    print(f"Update config.py with: ACCEL_BIAS = {bias.tolist()}")
    
    return bias


def get_all():
    """
    Returns combined sensor data: (ax, ay, az, gx, gy, gz)
    """
    accel = get_accel()
    gx, gy, gz = get_gyro()
    return accel[0], accel[1], accel[2], gx, gy, gz


# ===== TEST MODES =====

def test_raw_readings(duration=10):
    """Test mode: Display raw sensor readings"""
    print("=== Testing Raw IMU Readings ===")
    init_imu()
    
    start_time = time.time()
    try:
        while (time.time() - start_time) < duration:
            ax, ay, az = get_accel_raw()
            gx, gy, gz = get_gyro()
            
            print(f"Accel: [{ax:6.2f}, {ay:6.2f}, {az:6.2f}] m/s² | "
                  f"Gyro: [{gx:6.2f}, {gy:6.2f}, {gz:6.2f}] °/s")
            
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    
    print("Raw readings test complete")


def test_integration(duration=10):
    """Test mode: Display integrated velocity and position"""
    print("=== Testing IMU Integration ===")
    print(f"Running at ~{IMU_FREQUENCY} Hz")
    
    init_imu()
    reset_integration()
    
    dt = 1.0 / IMU_FREQUENCY
    start_time = time.time()
    
    try:
        while (time.time() - start_time) < duration:
            result = integrate_step(dt)
            
            v = result['velocity']
            p = result['position']
            
            print(f"Vel: [{v[0]:6.3f}, {v[1]:6.3f}, {v[2]:6.3f}] m/s | "
                  f"Pos: [{p[0]:6.3f}, {p[1]:6.3f}, {p[2]:6.3f}] m")
            
            time.sleep(dt)
    except KeyboardInterrupt:
        pass
    
    final_pos = get_position()
    print(f"\nFinal displacement: {final_pos} meters")
    print("Integration test complete")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "calibrate":
        # Run calibration mode
        calibrate_bias(samples=200, duration=10)
    
    elif len(sys.argv) > 1 and sys.argv[1] == "integrate":
        # Test integration
        test_integration(duration=20)
    
    else:
        # Default: raw readings
        test_raw_readings(duration=10)
    
    print("\nUsage:")
    print("  python imu.py              # Test raw readings")
    print("  python imu.py calibrate    # Calibrate bias")
    print("  python imu.py integrate    # Test integration")