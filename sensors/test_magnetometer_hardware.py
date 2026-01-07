# tests/test_magnetometer_hardware.py
import time
import statistics
from magnetometer import read_mag_raw, get_heading_basic

SAMPLES = 200
DELAY = 0.05  # seconds

mx_vals, my_vals, mz_vals, headings = [], [], [], []

print("Keep the sensor completely still...")
time.sleep(3)

for _ in range(SAMPLES):
    mx, my, mz = read_mag_raw()
    heading = get_heading_basic()

    mx_vals.append(mx)
    my_vals.append(my)
    mz_vals.append(mz)
    headings.append(heading)

    time.sleep(DELAY)

def report(name, values):
    print(
        f"{name}: mean={statistics.mean(values):.2f}, "
        f"std={statistics.stdev(values):.2f}"
    )

print("\nRaw magnetometer stability:")
report("mx", mx_vals)
report("my", my_vals)
report("mz", mz_vals)

print("\nHeading stability:")
report("heading (deg)", headings)
