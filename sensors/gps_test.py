"""
Purpose: Continuously stream latitude and longitude from gpsd at 1 Hz.
Concepts: gpsd socket interface, fix validation, rate limiting.
Integration: Coexists with cgps; gpsd owns the serial device.
"""

import gpsd
import time
import math

def stream_gps(rate_hz=1):
    gpsd.connect()

    period = 1.0 / rate_hz
    last_print = 0

    while True:
        packet = gpsd.get_current()

        # gpsd uses NaN until a fix exists
        has_fix = (
            packet.mode >= 2 and
            not math.isnan(packet.lat) and
            not math.isnan(packet.lon)
        )

        now = time.time()
        if now - last_print >= period:
            if has_fix:
                print(f"Lat: {packet.lat:.6f}, Lon: {packet.lon:.6f}")
            else:
                print("Waiting for GPS fix...")
            last_print = now

        time.sleep(0.1)  # small sleep to avoid busy loop

if __name__ == "__main__":
    try:
        stream_gps(rate_hz=1)
    except KeyboardInterrupt:
        print("\nGPS stream stopped")
