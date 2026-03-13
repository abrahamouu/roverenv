import time
from magnetometer import get_heading_basic

while True:
    heading = get_heading_basic()
    print(f"Heading: {heading:.2f}°")
    time.sleep(0.5)