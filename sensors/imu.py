# sensors/imu.py
import time
from mpu6050 import mpu6050  # your class file

_imu = None  # global instance


def init_imu(address=0x68):
    """
    Initialize the MPU6050 IMU.
    Creates the sensor once—safe to call multiple times.
    """
    global _imu
    if _imu is None:
        _imu = mpu6050(address)
    return _imu


def get_accel():
    """
    Returns accelerometer data in m/s^2
    (ax, ay, az)
    """
    imu = init_imu()
    data = imu.get_accel_data()   # your class already converts to m/s²
    return data['x'], data['y'], data['z']


def get_gyro():
    """
    Returns gyro data in deg/sec
    (gx, gy, gz)
    """
    imu = init_imu()
    data = imu.get_gyro_data()
    return data['x'], data['y'], data['z']


def get_all():
    """
    Returns both: (ax, ay, az, gx, gy, gz)
    """
    ax, ay, az = get_accel()
    gx, gy, gz = get_gyro()
    return ax, ay, az, gx, gy, gz


# Quick test mode (optional)
if __name__ == "__main__":
    imu = init_imu()
    print("MPU6050 Initialized")

    try:
        while True:
            ax, ay, az = get_accel()
            gx, gy, gz = get_gyro()

            print(f"Ax:{ax:.2f} Ay:{ay:.2f} Az:{az:.2f} | "
                  f"Gx:{gx:.2f} Gy:{gy:.2f} Gz:{gz:.2f}")

            time.sleep(0.2)

    except KeyboardInterrupt:
        print("IMU test stopped.")