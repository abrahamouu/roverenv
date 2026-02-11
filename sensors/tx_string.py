import numpy as np

PREAMBLE = "1010101010101010"  # 16-bit sync pattern

def string_to_bits(s: str):
    data_bits = ''.join(f"{c:08b}" for c in s.encode("utf-8"))
    framed = PREAMBLE + data_bits
    return np.array([int(b) for b in framed], dtype=np.uint8)

def bits_to_bpsk(bits, amplitude=12000, samples_per_bit=10):
    symbols = amplitude * (2 * bits - 1)
    return np.repeat(symbols, samples_per_bit).astype(np.complex64)

def transmit_string(sdr, message: str):
    bits = string_to_bits(message)
    samples = bits_to_bpsk(bits)

    sdr.setup_tx_buffer(len(samples))
    sdr.transmit_samples(samples)

    print("Transmitted:", message)
