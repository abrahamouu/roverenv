from magnetometer import get_heading_basic
import time

for _ in range(20):
    print(f"Heading: {get_heading_basic():.1f}°")
    time.sleep(0.5)