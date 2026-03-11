import time
import config
from imu import init_imu
from magnetometer import init_mag
from gpsmanager import init_gps, get_position
from coordinate_transform import set_reference_point, latlon_to_xy
from navigation import Navigator
import motor_helper
from sharedstate import control_state, state_lock


class RoverController:
    def __init__(self):
        print("Initializing rover systems...")

        init_imu()
        init_mag()
        init_gps()

        self.nav = Navigator()

        lat, lon = self._wait_for_gps_fix(max_attempts=30)
        if lat is None:
            raise RuntimeError("Could not get GPS fix during initialization. "
                               "Check antenna and gpsd service.")

        set_reference_point(lat, lon)
        self.nav.hard_reset_position(0, 0)
        print(f"Rover initialized at: {lat:.6f}, {lon:.6f}")

        self.last_gps_update = time.time()
        self.running = False

    def _wait_for_gps_fix(self, max_attempts=30):
        print(f"Waiting for GPS fix (up to {max_attempts}s)...")
        for attempt in range(max_attempts):
            lat, lon = get_position()
            if lat is not None and lon is not None:
                print(f"GPS fix acquired after {attempt + 1}s")
                return lat, lon
            time.sleep(1)
        print("WARNING: GPS fix not obtained.")
        return None, None

    def update_from_gps(self):
        lat, lon = get_position()
        if lat is not None and lon is not None:
            x, y = latlon_to_xy(lat, lon)
            self.nav.reset_position(x, y)
            if config.DEBUG_PRINT_NAVIGATION:
                print(f"GPS resync: ({x:.2f}, {y:.2f})")
            return lat, lon
        return None, None
    
    def set_destination_latlon(self, dest_lat, dest_lon):
        dest_x, dest_y = latlon_to_xy(dest_lat, dest_lon)
        self.nav.set_destination(dest_x, dest_y)
        print(f"Destination: {dest_lat:.6f}, {dest_lon:.6f} -> ({dest_x:.1f}m, {dest_y:.1f}m)")

    def set_destination_xy(self, x, y):
        self.nav.set_destination(x, y)

    # control loop
    def control_loop(self):
        stop = False
        new_dest = None

        with state_lock:
            stop = control_state.get("stop", False)

            if control_state.get("updated", False):
                new_dest = (control_state["dest_x"], control_state["dest_y"])
                control_state["updated"] = False

            config.BASE_SPEED = control_state.get("base_speed", config.BASE_SPEED)
            config.TURN_SPEED = control_state.get("turn_speed", config.TURN_SPEED)

        if stop:
            motor_helper.stop()
            self.running = False
            return

        if new_dest is not None:
            self.set_destination_xy(*new_dest)

        command, speed = self.nav.get_navigation_command()

        # Update only when moving forward
        if command == 'forward':
            state = self.nav.update_position()
            if state is None:
                return
        else:
            from magnetometer import get_heading_basic
            state = {
                'x': self.nav.x,
                'y': self.nav.y,
                'vx': self.nav.vx,
                'vy': self.nav.vy,
                'heading': get_heading_basic(),
                'ax_body': 0, 'ay_body': 0, 'az_body': 0,
                'ax_earth': 0, 'ay_earth': 0
            }

        # ---- MOTOR COMMANDS ----
        if command == 'forward':
            motor_helper.forward(speed)
            time.sleep(0.1)
        elif command == 'turn_left':
            motor_helper.turn_left(speed)
            time.sleep(0.4)
            motor_helper.stop()
            time.sleep(0.1)
        elif command == 'turn_right':
            motor_helper.turn_right(speed)
            time.sleep(0.4)
            motor_helper.stop()
            time.sleep(0.1)
        elif command == 'stop':
            motor_helper.stop()
            self.running = False

        # ---- DEBUG ----
        if config.DEBUG_PRINT_NAVIGATION:
            dist = self.nav.get_distance_to_destination()
            heading_err = self.nav.get_heading_error()
            print(f"Pos:({state['x']:.1f},{state['y']:.1f}) "
                  f"Heading:{state['heading']:.1f}° "
                  f"Dist:{dist:.1f}m HErr:{heading_err:.1f}° Cmd:{command}")

    def run(self):
        self.running = True
        loop_time = 1.0 / config.IMU_FREQUENCY

        print("Starting navigation...")

        try:
            while self.running and not self.nav.has_reached_destination():
                start = time.time()

                self.control_loop()

                elapsed = time.time() - start
                if elapsed < loop_time:
                    time.sleep(loop_time - elapsed)

            motor_helper.stop()
            self.running = False 
            print("Navigation complete!")

        except KeyboardInterrupt:
            print("\nStopping...")
            motor_helper.stop()

# testing node traversal
if __name__ == "__main__":
    rover = RoverController()

    # Set destination in meters relative to start:
    # set_destination_xy(east/west, north/south)
    # Examples:
    #   rover.set_destination_xy(-3, 0)   # 3m West
    #   rover.set_destination_xy(0, 5)    # 5m North
    #   rover.set_destination_xy(3, 3)    # 3m East, 3m North
    rover.set_destination_xy(-3, 0)

    rover.run()