from sdr_control import PlutoSDR
from tx_string import transmit_string

sdr = PlutoSDR(uri="ip:192.168.2.1")

sdr.set_tx_frequency(2_400_000_000)
sdr.set_sample_rate(4_000_000)
sdr.set_tx_bandwidth(1_000_000)
sdr.set_tx_gain(-10)

transmit_string(sdr, "HELLO")

input("Press Enter to stop...")

sdr.close()
