from motor_helper import turn_left, turn_right, stop
import time

print("Testing LEFT rotation...")
turn_left(1)
time.sleep(2)
stop()
time.sleep(1)

print("Testing RIGHT rotation...")
turn_right(1)
time.sleep(2)
stop()
