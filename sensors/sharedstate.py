import threading
import config

control_state = {
    "dest_x": 0.0,
    "dest_y": 0.0,
    "base_speed": config.BASE_SPEED,
    "turn_speed": config.TURN_SPEED,
    "updated": False,
    "stop": False,
}

state_lock = threading.Lock()
