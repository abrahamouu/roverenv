# movement_test.py
from time import sleep
import motor_helper as mh

def run_movement_test():
    try:
        mh.stop()
        sleep(1)

        print("testing forward")
        mh.forward(0.5)
        sleep(2)

        print("testing backward")
        mh.backward(0.5)
        sleep(2)

        print("testing stop")
        mh.stop()
        sleep(2)

        print("testing turn left")
        mh.turn_left(1.0)
        sleep(2)
        mh.stop()
        sleep(1)

        print("testing turn right")
        mh.turn_right(1.0)
        sleep(2)

        mh.stop()
        print("movement test complete")

    except Exception as e:
        mh.stop()
        raise e
