
import time
import math
import config
from imu import get_accel
from magnetometer import get_heading_basic
from coordinate_transform import (
    body_to_earth_frame,
    angle_difference,
    distance_2d,
    bearing_to_point
)

class Navigator:
    def __init__(self):
        # Current state
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0

        # Destination
        self.dest_x = None
        self.dest_y = None

        # Timing
        self.last_update_time = None
        self.last_gps_sync = time.time()
        self._accel_noise_threshold = config.ACCEL_NOISE_THRESHOLD

        print(f"Navigator initialized (IMU freq: {config.IMU_FREQUENCY}Hz)")

    def set_destination(self, x, y):
        self.dest_x = x
        self.dest_y = y
        dist = self.get_distance_to_destination()
        print(f"Destination set: ({x:.1f}, {y:.1f}), distance: {dist:.2f}m")

    def reset_position(self, x, y):
        time_since_sync = time.time() - self.last_gps_sync
        gps_weight = min(1.0, time_since_sync / config.GPS_UPDATE_INTERVAL)

        self.x = (1 - gps_weight) * self.x + gps_weight * x
        self.y = (1 - gps_weight) * self.y + gps_weight * y

        self.vx = 0.0
        self.vy = 0.0
        self.last_gps_sync = time.time()
        print(f"GPS correction (weight={gps_weight:.2f}): ({self.x:.2f}, {self.y:.2f})")

    def hard_reset_position(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.last_gps_sync = time.time()
        print(f"Position hard reset: ({x:.2f}, {y:.2f})")

    def _is_moving(self, ax, ay):
        accel_magnitude = math.sqrt(ax**2 + ay**2)
        return accel_magnitude > self._accel_noise_threshold

    def update_position(self):
        current_time = time.time()
        if self.last_update_time is None:
            self.last_update_time = current_time
            return None

        dt = current_time - self.last_update_time
        self.last_update_time = current_time
        dt = min(dt, 0.1)

        ax_body, ay_body, az_body = get_accel()
        heading = get_heading_basic()

        # Apply bias
        ax_body -= config.ACCEL_BIAS_X
        ay_body -= config.ACCEL_BIAS_Y
        az_body -= 9.80665

        accel_magnitude = math.sqrt(ax_body**2 + ay_body**2)
        is_moving = accel_magnitude > config.ACCEL_NOISE_THRESHOLD

        if is_moving:
            # fixed speed model
            speed = config.ESTIMATED_SPEED
            heading_rad = math.radians(heading)
            self.vx = speed * math.sin(heading_rad)
            self.vy = speed * math.cos(heading_rad)
        else:
            # velocity delay quickly when stopped
            self.vx *= 0.5
            self.vy *= 0.5

        self.x += self.vx * dt
        self.y += self.vy * dt

        return {
            'x': self.x,
            'y': self.y,
            'vx': self.vx,
            'vy': self.vy,
            'ax_body': ax_body,
            'ay_body': ay_body,
            'az_body': az_body,
            'ax_earth': 0,
            'ay_earth': 0,
            'heading': heading
        }

    def get_distance_to_destination(self):
        if self.dest_x is None or self.dest_y is None:
            return float('inf')
        return distance_2d(self.x, self.y, self.dest_x, self.dest_y)

    def get_bearing_to_destination(self):
        if self.dest_x is None or self.dest_y is None:
            return None
        return bearing_to_point(self.x, self.y, self.dest_x, self.dest_y)

    def get_heading_error(self):
        target_bearing = self.get_bearing_to_destination()
        if target_bearing is None:
            return 0.0
        current_heading = get_heading_basic()
        return angle_difference(target_bearing, current_heading)

    def has_reached_destination(self):
        return self.get_distance_to_destination() < config.POSITION_EPSILON

    def should_resync_gps(self):
        return time.time() - self.last_gps_sync > config.GPS_UPDATE_INTERVAL

    def get_navigation_command(self):
        if self.has_reached_destination():
            return 'stop', 0.0

        dist = self.get_distance_to_destination()
        if dist < config.MIN_MOVE_DISTANCE:
            return 'stop', 0.0

        heading_error = self.get_heading_error()

        if abs(heading_error) > config.HEADING_TOLERANCE:
            if heading_error > 0:
                return 'turn_right', config.TURN_SPEED
            else:
                return 'turn_left', config.TURN_SPEED

        return 'forward', config.BASE_SPEED