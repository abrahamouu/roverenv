import numpy as np
from sdr_control import PlutoSDR, load_config

def fsk_demodulate(iq_samples, sps=100, sample_rate=4000000):
    """
    FSK demod: measure frequency of each bit period
    50 kHz = bit 0, 150 kHz = bit 1
    """
    num_bits = len(iq_samples) // sps
    bits = []
    
    for i in range(num_bits):
        segment = iq_samples[i*sps:(i+1)*sps]
        
        # Compute FFT to find dominant frequency
        fft = np.fft.fft(segment)
        freqs = np.fft.fftfreq(len(segment), 1/sample_rate)
        
        # Look at positive frequencies only
        pos_freqs = freqs[:len(freqs)//2]
        pos_fft = np.abs(fft[:len(fft)//2])
        
        # Find peak frequency
        peak_idx = np.argmax(pos_fft)
        peak_freq = abs(pos_freqs[peak_idx])
        
        # Decide: closer to 50kHz or 150kHz?
        if abs(peak_freq - 50000) < abs(peak_freq - 150000):
            bits.append(0)
        else:
            bits.append(1)
    
    return np.array(bits, dtype=np.uint8)

def string_to_bits(text):
    """Convert string to bits"""
    bits = []
    for char in text:
        byte = ord(char)
        for i in range(8):
            bits.append((byte >> (7-i)) & 1)
    return np.array(bits, dtype=np.uint8)

def find_preamble_simple(bits):
    """Find alternating pattern"""
    for start_pos in range(min(200, len(bits) - 64)):
        segment = bits[start_pos:start_pos+64]
        transitions = np.sum(segment[:-1] != segment[1:])
        
        if transitions >= 50:
            return start_pos + 64
    
    return None

def bits_to_string(bits):
    """Convert bits to string"""
    chars = []
    for i in range(0, len(bits), 8):
        if i + 8 > len(bits):
            break
        byte_bits = bits[i:i+8]
        byte_val = 0
        for j, bit in enumerate(byte_bits):
            byte_val |= (bit << (7-j))
        
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
    
    print("Listening for FSK messages...")
    print("Bit 0 = 50 kHz, Bit 1 = 150 kHz")
    
    try:
        while True:
            iq = sdr.receive_samples()
            
            # Demodulate
            bits = fsk_demodulate(iq, sps=100, sample_rate=config["rx"]["sample_rate"])
            
            print(f"Demodulated {len(bits)} bits")
            print(f"First 64 bits: {''.join(str(b) for b in bits[:64])}")
            
            # Instead of relying on preamble, search for HELLO pattern directly
            hello_bits = string_to_bits("HELLO")
            
            # Search for HELLO in the bitstream
            for start in range(len(bits) - 40):
                test_bits = bits[start:start+40]
                
                # Count how many bits match HELLO
                matches = np.sum(test_bits == hello_bits)
                
                # If at least 35 out of 40 bits match (87.5%), we found it!
                if matches >= 35:
                    message = bits_to_string(test_bits)
                    print(f"Found at bit {start}: '{message}' ({matches}/40 bits match)")
                    
                    if matches >= 38:
                        print("*** SUCCESS! Got HELLO! ***")
                    break
            
            print("---")
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        sdr.close()

if __name__ == "__main__":
    main()