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

def simple_bpsk_modulate(bits, sps=40):
    """Simple BPSK: 0->-1, 1->+1, then upsample"""
    symbols = 2*bits - 1  # Convert to -1, +1
    upsampled = np.repeat(symbols, sps)  # Repeat each symbol sps times
    
    iq = upsampled.astype(np.complex64)
    iq *= 0.8 * (2**14)  # Scale for Pluto
    
    return iq

def main():
    config = load_config("config.json")
    sdr = PlutoSDR(uri=config["connection"]["uri"])

    sdr.set_tx_frequency(config["tx"]["frequency"])
    sdr.set_tx_sample_rate(config["tx"]["sample_rate"])
    sdr.set_tx_bandwidth(config["tx"]["bandwidth"])
    sdr.set_tx_gain(0)

    # Message to send
    message = "HELLO"
    
    # Add preamble for sync (alternating 1010...)
    preamble_bits = np.tile([1, 0], 32)  # 64 bits of alternating
    
    # Convert message to bits
    data_bits = string_to_bits(message)
    
    # Combine: preamble + data
    all_bits = np.concatenate([preamble_bits, data_bits])
    
    # Modulate
    iq = simple_bpsk_modulate(all_bits, sps=40)
    
    print(f"Transmitting: '{message}'")
    print(f"Total bits: {len(all_bits)} (preamble: {len(preamble_bits)}, data: {len(data_bits)})")
    print(f"Total samples: {len(iq)}")
    
    sdr.setup_tx_buffer(len(iq))
    
    print("Sending continuously (Ctrl+C to stop)...")
    
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