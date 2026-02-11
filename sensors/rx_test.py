from sdr_control import PlutoSDR
import numpy as np

sdr = PlutoSDR(uri="ip:192.168.2.1")

sdr.set_rx_frequency(2_400_000_000)
sdr.set_sample_rate(4_000_000)
sdr.set_rx_bandwidth(1_000_000)
sdr.set_rx_gain_mode("slow_attack")

sdr.setup_rx_buffer(4096)

samples = sdr.receive_samples()
print("RX power:", np.mean(np.abs(samples)))

sdr.close()
