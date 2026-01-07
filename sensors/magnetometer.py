# sensors/magnetometer.py
import math
from bmm150 import BMM150

_mag = None

def init_mag():
    global _mag
    if _mag is None:
        _mag = BMM150()
    return _mag


def read_mag_raw():
    """
    Returns raw magnetometer values (mx, my, mz)
    """
    global _mag
    if _mag is None:
        init_mag()

    mx, my, mz = _mag.read_mag_data()
    return mx, my, mz


def get_heading_basic():
    """
    Simple heading (NOT tilt compensated).
    """
    mx, my, mz = read_mag_raw()

    heading = math.degrees(math.atan2(my, mx))
    if heading < 0:
        heading += 360

    return heading