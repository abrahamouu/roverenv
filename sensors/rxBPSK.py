import numpy as np
from sdr_control import PlutoSDR, load_config

def simple_bpsk_demodulate(iq_samples, sps=40):
    """Simple BPSK demod: just sample every sps samples and check sign"""
    # Take one sample per symbol
    symbols = iq_samples[::sps].real
    
    # Convert to bits: positive = 1, negative = 0
    bits = (symbols > 0).astype(np.uint8)
    
    return bits

def find_preamble_simple(bits):
    """Find alternating 10101010... pattern (64 bits)"""
    preamble = np.tile([1, 0], 32)
    
    # Search for preamble with some tolerance
    for i in range(len(bits) - len(preamble)):
        # Count how many bits match
        matches = np.sum(bits[i:i+len(preamble)] == preamble)
        
        # If at least 90% match, we found it
        if matches > len(preamble) * 0.9:
            return i + len(preamble)  # Return position after preamble
    
    return None

def bits_to_string(bits):
    """Convert bits back to string"""
    chars = []
    for i in range(0, len(bits), 8):
        if i + 8 > len(bits):
            break
        byte_bits = bits[i:i+8]
        byte_val = 0
        for j, bit in enumerate(byte_bits):
            byte_val |= (bit << (7-j))
        
        # Only add printable ASCII
        if 32 <= byte_val <= 126:
            chars.append(chr(byte_val))
    
    return ''.join(chars)

def main():
    config = load_config("config.json")
    sdr = PlutoSDR(uri=config["connection"]["uri"])

    sdr.set_rx_frequency(config["rx"]["frequency"])
    sdr.set_rx_sample_rate(config["rx"]["sample_rate"])
    sdr.set_rx_bandwidth(config["rx"]["bandwidth"])
    sdr.set_rx_gain_mode("manual")
    sdr.set_rx_gain(50)

    sdr.setup_rx_buffer(131072)
    
    print("Listening for messages...")
    print("(Looking for 'HELLO')")
    
    try:
        while True:
            # Receive samples
            iq = sdr.receive_samples()
            
            # Demodulate to bits
            bits = simple_bpsk_demodulate(iq, sps=40)
            
            # Find preamble
            data_start = find_preamble_simple(bits)
            
            if data_start is not None:
                # Extract data after preamble
                data_bits = bits[data_start:data_start+40]  # 5 chars * 8 bits = 40 bits
                
                # Convert to string
                message = bits_to_string(data_bits)
                
                if message:
                    print(f"\n✓ Received: '{message}'")
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        sdr.close()

if __name__ == "__main__":
    main()