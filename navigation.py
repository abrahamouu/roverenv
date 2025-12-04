# navigation.py

import math
import time

from sensors.gps import get_gps
from sensors.heading import get_heading_tilt_compensated

# Import your motor functions
from motor_control import forward, stop, turn_left, turn_right

# -----------------------------
# Distance + Bearing Functions
# -----------------------------

def distance_between(lat1, lon1, lat2, lon2):
    R = 6371000  # meters
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    φ1 = math.radians(lat1)
    φ2 = math.radians(lat2)

    a = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def bearing_to_target(lat1, lon1, lat2, lon2):
    φ1 = math.radians(lat1)
    φ2 = math.radians(lat2)
    Δλ = math.radians(lon2 - lon1)

    y = math.sin(Δλ) * math.cos(φ2)
    x = math.cos(φ1)*math.sin(φ2) - math.sin(φ1)*math.cos(φ2)*math.cos(Δλ)

    brng = math.degrees(math.atan2(y, x))
    return (brng + 360) % 360


def heading_error(target, current):
    # output between -180..180
    return (target - current + 540) % 360 - 180



# -----------------------------
# Main Navigation to Node
# -----------------------------

def go_to_node(target_lat, target_lon):
    ARRIVAL_RADIUS = 1.0  # meters (adjust after testing)

    print("Starting navigation...")
    print(f"Target: {target_lat}, {target_lon}")

    while True:
        # ---------- GPS ----------
        lat, lon = get_gps()
        if lat is None:
            print("Waiting for GPS fix...")
            time.sleep(1)
            continue

        # ---------- Heading ----------
        heading = get_heading_tilt_compensated()

        # ---------- Bearing + Distance ----------
        dist = distance_between(lat, lon, target_lat, target_lon)
        bearing = bearing_to_target(lat, lon, target_lat, target_lon)

        print(f"Dist={dist:.2f} m | Bearing={bearing:.2f}° | Heading={heading:.2f}°")

        # ---------- Arrival ----------
        if dist < ARRIVAL_RADIUS:
            stop()
            print("Reached node!")
            break

        # ---------- Compute Heading Error ----------
        err = heading_error(bearing, heading)

        # ---------- Navigation Logic ----------
        if abs(err) > 15:
            # Rover is not facing the target → rotate in place
            print(f"Large error ({err:.2f}) — rotating...")
            if err > 0:
                turn_right(1)
            else:
                turn_left(1)

        elif abs(err) > 4:
            if err > 0:
                turn_right(1)
            else:
                turn_left(1)
        else:
            forward(0.7)
        time.sleep(0.2)
