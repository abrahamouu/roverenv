import numpy as np
from sdr_control import PlutoSDR, load_config

def simple_bpsk_demodulate(iq_samples, sps=40):
    """Simple BPSK demod: try all phases and pick the best"""
    best_bits = None
    best_energy = 0
    
    # Try different sampling offsets (phases)
    for phase in range(sps):
        symbols = iq_samples[phase::sps].real
        energy = np.sum(symbols**2)
        
        if energy > best_energy:
            best_energy = energy
            best_bits = (symbols > 0).astype(np.uint8)
    
    return best_bits

def find_preamble_simple(bits):
    """Find alternating 10101010... pattern - very lenient"""
    
    # Look for at least 40 bits of mostly alternating pattern
    for start_pos in range(min(200, len(bits) - 64)):
        # Count transitions (bit changes) in next 64 bits
        segment = bits[start_pos:start_pos+64]
        transitions = np.sum(segment[:-1] != segment[1:])
        
        # Alternating pattern should have ~63 transitions in 64 bits
        # Accept if at least 50 transitions (about 80%)
        if transitions >= 50:
            print(f"Found alternating pattern at {start_pos}, transitions: {transitions}/63")
            return start_pos + 64  # Return position after preamble
    
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
            
            print(f"Received {len(iq)} samples, max power: {np.max(np.abs(iq)):.1f}")
            
            # Demodulate to bits
            bits = simple_bpsk_demodulate(iq, sps=40)
            
            print(f"Demodulated to {len(bits)} bits")
            print(f"First 100 bits: {''.join(str(b) for b in bits[:100])}")
            
            # Find preamble
            data_start = find_preamble_simple(bits)
            
            if data_start is not None:
                print(f"Found preamble at bit {data_start}")
                
                # Skip a few extra bits as guard interval to avoid preamble remnants
                data_start += 8  # Skip 8 more bits to be safe
                
                # Extract exactly 40 bits for "HELLO"
                if data_start + 40 <= len(bits):
                    data_bits = bits[data_start:data_start+40]
                    
                    print(f"Data bits: {''.join(str(b) for b in data_bits)}")
                    
                    # Convert to string
                    message = bits_to_string(data_bits)
                    
                    if message and len(message) >= 3:  # Should get at least 3 chars
                        print(f"✓ Received: '{message}'")
                        
                        # Check if it's actually HELLO
                        if 'HELLO' in message or 'HELL' in message or 'ELLO' in message:
                            print(f"*** SUCCESS! Got HELLO! ***")
            else:
                print("No preamble found")
            
            print("---")
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        sdr.close()

if __name__ == "__main__":
    main()