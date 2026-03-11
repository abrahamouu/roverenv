# movement_test.py
from time import sleep, time
import motor_helper as mh
from interrupt import STOP_EVENT

CHECK_INTERVAL = 0.05  # 50ms interrupt resolution

def interruptible_sleep(duration):
    start = time()
    while time() - start < duration:
        if STOP_EVENT.is_set():
            mh.stop()
            return False
        sleep(CHECK_INTERVAL)
    return True

def run_movement_test():
    try:
        STOP_EVENT.clear()
        mh.stop()

        if not interruptible_sleep(1): return

        print("testing forward")
        mh.forward(0.5)
        if not interruptible_sleep(2): return

        print("testing backward")
        mh.backward(0.5)
        if not interruptible_sleep(2): return

        print("testing stop")
        mh.stop()
        if not interruptible_sleep(2): return

        print("testing turn left")
        mh.turn_left(1.0)
        if not interruptible_sleep(2): return
        mh.stop()
        if not interruptible_sleep(1): return

        print("testing turn right")
        mh.turn_right(1.0)
        if not interruptible_sleep(2): return

        mh.stop()
        print("movement test complete")

    except Exception as e:
        mh.stop()
        raise e
