import numpy as np

def string_to_bits(s: str):
    return np.array(
        [int(b) for c in s.encode("utf-8") for b in f"{c:08b}"],
        dtype=np.uint8,
    )

def bits_to_bpsk(bits, amplitude=12000):
    return amplitude * (2 * bits - 1) + 0j

def transmit_string(sdr, message: str):
    bits = string_to_bits(message)
    samples = bits_to_bpsk(bits)
    sdr.setup_tx_buffer(len(samples))
    sdr.transmit_samples(samples)
