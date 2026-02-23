from imu import init_imu, get_accel
init_imu()
import time

readings = []
print("Collecting 500 samples, keep rover still...")
for _ in range(500):       # was 100, more samples = more stable average
    readings.append(get_accel())
    time.sleep(0.02)

avg_x = sum(r[0] for r in readings) / len(readings)
avg_y = sum(r[1] for r in readings) / len(readings)
print(f"ACCEL_BIAS_X = {avg_x:.4f}")
print(f"ACCEL_BIAS_Y = {avg_y:.4f}")