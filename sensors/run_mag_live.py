import time
import math
from collections import deque
from magnetometer import read_mag_raw, get_heading_basic

WINDOW = 20          # rolling window size
DELAY = 0.1          # seconds between reads

mx_w = deque(maxlen=WINDOW)
my_w = deque(maxlen=WINDOW)
mz_w = deque(maxlen=WINDOW)
h_w  = deque(maxlen=WINDOW)

def circular_stdev(deg_angles):
    """ 
    Circular standard deviation for angles in degrees.
    Correctly handles wrap-around at 0°/360° by treating angles as
    unit vectors on a circle instead of linear values. 
    ** Box-Muller Transform = sqrt(-2 * ln(R))
    """
    if len(deg_angles) < 2:
        return 0.0
    
    rad = [math.radians(a) for a in deg_angles]
  
    #Fetch x and y axis vectors
    sin_mean = sum(math.sin(a) for a in rad) / len(rad)
    cos_mean = sum(math.cos(a) for a in rad) / len(rad)
    R = math.sqrt(sin_mean**2 + cos_mean**2)

    if R <= 0:
        return 180.0
    
    return math.degrees(math.sqrt(-2 * math.log(R)))

print("Live magnetometer test")
print("Move the sensor slowly. Press Ctrl+C to stop.\n")

try:
    while True:
        mx, my, mz = read_mag_raw()
        h = get_heading_basic()

        mx_w.append(mx)
        my_w.append(my)
        mz_w.append(mz)
        h_w.append(h)

        if len(h_w) >= 5:
            σh = circular_stdev(h_w)
            print(
                f"mx={mx:7.1f}  my={my:7.1f}  mz={mz:7.1f} | "
                f"h={h:6.1f}° | "
                f"σh={σh:4.2f}"
            )
        else:
            print(
                f"mx={mx:7.1f}  my={my:7.1f}  mz={mz:7.1f} | "
                f"h={h:6.1f}°"
            )

        time.sleep(DELAY)

except KeyboardInterrupt:
    print("\nStopped.")
