import numpy as np

PREAMBLE = "1010101010101010"
SAMPLES_PER_BIT = 10

def bpsk_demodulate(samples):
    # Downsample by taking center sample of each bit
    samples = samples.reshape(-1, SAMPLES_PER_BIT)
    center_samples = samples[:, SAMPLES_PER_BIT // 2]

    bits = (np.real(center_samples) > 0).astype(np.uint8)
    return bits

def bits_to_string(bits):
    bit_str = ''.join(str(b) for b in bits)

    # Find preamble
    idx = bit_str.find(PREAMBLE)
    if idx == -1:
        return "No preamble found"

    data = bit_str[idx + len(PREAMBLE):]

    chars = []
    for i in range(0, len(data), 8):
        byte = data[i:i+8]
        if len(byte) < 8:
            break
        chars.append(chr(int(byte, 2)))

    return ''.join(chars)
