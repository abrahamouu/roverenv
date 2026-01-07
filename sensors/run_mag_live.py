import time
import statistics
from collections import deque
from magnetometer import read_mag_raw, get_heading_basic

WINDOW = 20          # rolling window size
DELAY = 0.1          # seconds between reads

mx_w = deque(maxlen=WINDOW)
my_w = deque(maxlen=WINDOW)
mz_w = deque(maxlen=WINDOW)
h_w  = deque(maxlen=WINDOW)

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
            print(
                f"mx={mx:7.1f}  my={my:7.1f}  mz={mz:7.1f} | "
                f"h={h:6.1f}° | "
                f"σh={statistics.stdev(h_w):4.2f}"
            )
        else:
            print(
                f"mx={mx:7.1f}  my={my:7.1f}  mz={mz:7.1f} | "
                f"h={h:6.1f}°"
            )

        time.sleep(DELAY)

except KeyboardInterrupt:
    print("\nStopped.")
