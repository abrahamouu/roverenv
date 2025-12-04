import gps
import time

session = gps.gps(mode=gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
print("Testing GPS...")

while True:
    report = session.next()

    if report['class'] == 'TPV':
        lat = getattr(report, 'lat', None)
        lon = getattr(report, 'lon', None)

        if lat is not None and lon is not None:
            print(f"Lat:{lat}, Long:{lon}")