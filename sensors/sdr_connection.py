# make sure do pip install pylibiio 
# or on pi: sudo apt install libiio-dev python3-pylibiio
# ctx = iio.Context("ip:pluto.local")

import iio

try: 
    ctx = iio.Context("ip:192.168.2.1")
    print("Connected devices:")
    for d in ctx.devices:
        print(d.name)

except OSError as e:
    print("Could not connect to Pluto SDR. Please check your connection and try again.")
    print(f"Error details: {e}")
    exit(1)
except Exception as e:
    print("An unexpected error occurred while connecting to Pluto SDR.")
    print(f"Error details: {e}")
    exit(1)
