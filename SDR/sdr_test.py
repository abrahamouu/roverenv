# make sure do pip install pylibiio
# sudo apt install libiio-dev python3-pylibiio
# ctx = iio.Context("ip:pluto.local")

import iio

ctx = iio.Context("ip:192.168.2.1")
print("Connected devices:")
for d in ctx.devices:
    print(d.name)
