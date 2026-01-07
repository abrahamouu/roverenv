import gps

session = None

def init_gps():
    global session 
    if session is None:
        session = gps.gps(mode=gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
    return session

def get_gps():
    session = init_gps()
    report = session.next()

    if report['class'] != 'TPV':
        return None, None

    lat = getattr(report, 'lat', None)
    lon = getattr(report, 'lon', None)
    print(f"Latitude: {report.lat}, Longitude: {report.lon}")

    return lat, lon