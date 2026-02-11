from sdr_control import PlutoSDR
from rx_string import bpsk_demodulate, bits_to_string

sdr = PlutoSDR(uri="ip:192.168.2.1")

sdr.set_rx_frequency(915_000_000)
sdr.set_sample_rate(4_000_000)
sdr.set_rx_bandwidth(1_000_000)
sdr.set_rx_gain_mode("manual")
sdr.set_rx_gain(60)

sdr.setup_rx_buffer(50000)

samples = sdr.receive_samples()

bits = bpsk_demodulate(samples)
msg = bits_to_string(bits)

print("Received:", msg)

sdr.close()
