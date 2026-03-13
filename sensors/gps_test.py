import gpsd
import math

gpsd.connect()

def get_current_gps():
    """
    Returns a dictionary:
    {
        "lat": float | None,
        "lon": float | None,
        "has_fix": bool
    }
    """
    packet = gpsd.get_current()

    has_fix = (
        packet.mode >= 2 and
        not math.isnan(packet.lat) and
        not math.isnan(packet.lon)
    )

    if has_fix:
        return {
            "lat": packet.lat,
            "lon": packet.lon,
            "has_fix": True
        }

    return {
        "lat": None,
        "lon": None,
        "has_fix": False
    }