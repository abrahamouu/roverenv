import numpy as np

def bpsk_demodulate(samples):
    return (np.real(samples) > 0).astype(np.uint8)

def bits_to_string(bits):
    chars = []
    for i in range(0, len(bits) - 7, 8):
        byte = bits[i:i+8]
        chars.append(chr(int("".join(map(str, byte)), 2)))
    return "".join(chars)
