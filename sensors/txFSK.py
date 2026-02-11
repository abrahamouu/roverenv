import numpy as np
import time
from sdr_control import PlutoSDR, load_config

def string_to_bits(text):
    """Convert string to bits"""
    bits = []
    for char in text:
        byte = ord(char)
        for i in range(8):
            bits.append((byte >> (7-i)) & 1)
    return np.array(bits, dtype=np.uint8)

def fsk_modulate(bits, sps=100, sample_rate=4000000):
    """
    FSK: bit 0 = 50kHz tone, bit 1 = 150kHz tone
    Much more robust than BPSK!
    """
    freq_0 = 50000   # 50 kHz for bit 0
    freq_1 = 150000  # 150 kHz for bit 1
    
    samples_per_bit = sps
    t_bit = np.arange(samples_per_bit) / sample_rate
    
    signal = []
    for bit in bits:
        freq = freq_1 if bit == 1 else freq_0
        tone = np.exp(2j * np.pi * freq * t_bit)
        signal.extend(tone)
    
    iq = np.array(signal, dtype=np.complex64)
    iq *= 0.8 * (2**14)
    
    return iq

def main():
    config = load_config("config.json")
    sdr = PlutoSDR(uri=config["connection"]["uri"])

    sdr.set_tx_frequency(config["tx"]["frequency"])
    sdr.set_tx_sample_rate(config["tx"]["sample_rate"])
    sdr.set_tx_bandwidth(config["tx"]["bandwidth"])
    sdr.set_tx_gain(0)

    message = "HELLO"
    
    # Preamble: alternating bits
    preamble_bits = np.tile([1, 0], 32)  # 64 bits
    data_bits = string_to_bits(message)
    
    print(f"Transmitting '{message}' using FSK")
    print(f"Bit 0 = 50 kHz, Bit 1 = 150 kHz")
    
    # Send multiple copies
    packet = np.concatenate([preamble_bits, data_bits])
    all_bits = np.tile(packet, 3)
    
    iq = fsk_modulate(all_bits, sps=100, sample_rate=config["tx"]["sample_rate"])
    
    print(f"Total samples: {len(iq)}")
    
    sdr.setup_tx_buffer(len(iq))
    
    print("Sending continuously...")
    
    try:
        while True:
            sdr.transmit_samples(iq)
            print(".", end="", flush=True)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        sdr.close()

if __name__ == "__main__":
    main()