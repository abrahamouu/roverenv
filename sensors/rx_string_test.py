from sdr_control import PlutoSDR
from rx_string import bpsk_demodulate, bits_to_string

sdr = PlutoSDR(uri="ip:192.168.2.1")

sdr.set_rx_frequency(2_400_000_000)
sdr.set_sample_rate(4_000_000)
sdr.set_rx_bandwidth(1_000_000)
sdr.set_rx_gain_mode("slow_attack")

sdr.setup_rx_buffer(4096)

samples = sdr.receive_samples()
bits = bpsk_demodulate(samples)
msg = bits_to_string(bits)

print("Received:", msg)

sdr.close()
