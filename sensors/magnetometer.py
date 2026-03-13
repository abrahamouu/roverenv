import math
from bmm150 import BMM150

_mag = None

def init_mag():
    global _mag
    if _mag is None:
        _mag = BMM150()
    return _mag

def ensure_initialized():
    global _mag
    if _mag is None:
        init_mag()

def read_mag_raw():
    ensure_initialized()
    return _mag.read_mag_data()

def get_heading_basic():
    mx, my, mz = read_mag_raw()

    heading = math.degrees(math.atan2(-my, mx))
    # error w/ magnetometer
    heading += 20
    if heading < 0:
        heading += 360
    return heading
