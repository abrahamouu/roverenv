# interrupt.py (recommended new file)
import threading

STOP_EVENT = threading.Event()
MOTOR_LOCK = threading.Lock()
