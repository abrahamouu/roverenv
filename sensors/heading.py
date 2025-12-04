# sensors/heading.py
import math
from magnetometer import read_mag_raw
from imu import get_accel

def get_heading_tilt_compensated():
    """
    Combines BMM150 magnetometer + MPU6050 accelerometer
    to produce stable, tilt-compensated heading (0-360°).
    """

    mx, my, mz = read_mag_raw()
    ax, ay, az = get_accel()

    # Normalize accel vector
    norm = math.sqrt(ax*ax + ay*ay + az*az)
    ax /= norm
    ay /= norm
    az /= norm

    # Compute tilt angles
    pitch = math.asin(-ax)
    roll = math.atan2(ay, az)

    # Tilt-compensated mag axes
    xh = mx * math.cos(pitch) + mz * math.sin(pitch)
    yh = mx * math.sin(roll)*math.sin(pitch) + \
         my * math.cos(roll) - \
         mz * math.sin(roll)*math.cos(pitch)

    heading = math.degrees(math.atan2(yh, xh))

    if heading < 0:
        heading += 360

    return heading
