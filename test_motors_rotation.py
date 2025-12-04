from motor_control import turn_left, turn_right, stop
import time

print("Testing LEFT rotation...")
turn_left(0.8)
time.sleep(2)
stop()
time.sleep(1)

print("Testing RIGHT rotation...")
turn_right(0.8)
time.sleep(2)
stop()
