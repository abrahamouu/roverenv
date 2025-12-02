from bmm150 import BMM150
import time

sensor = BMM150()

while True:
    x, y, z = sensor.read_mag_data()
    print(x, y, z)
    time.sleep(0.1)
