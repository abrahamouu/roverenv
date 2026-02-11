# sdr_modem.py
import numpy as np

def string_to_bits(s: str) -> np.ndarray:
    b = s.encode("utf-8")
    bits = np.unpackbits(np.frombuffer(b, dtype=np.uint8))
    return bits

def bpsk_modulate(bits: np.ndarray, samples_per_symbol=20, amplitude=2**14):
    """
    0 -> -1
    1 -> +1
    """
    symbols = 2 * bits - 1  # 0->-1, 1->+1
    iq = np.repeat(symbols, samples_per_symbol).astype(np.float32)
    iq = iq * amplitude
    return iq.astype(np.complex64)

def bpsk_demodulate(iq: np.ndarray, samples_per_symbol=20):
    symbols = iq.real
    symbols = symbols.reshape(-1, samples_per_symbol).mean(axis=1)
    bits = (symbols > 0).astype(np.uint8)
    return bits

def bits_to_string(bits: np.ndarray) -> str:
    bytes_arr = np.packbits(bits)
    return bytes_arr.tobytes().decode("utf-8", errors="ignore")
