from sensors.gps import get_gps
import time

print("Testing GPS...")

while True:
    lat, lon = get_gps()
    if lat is None:
        print("Waiting for GPS fix...")
    else:
        print(f"Lat={lat}, Lon={lon}")
    time.sleep(1)