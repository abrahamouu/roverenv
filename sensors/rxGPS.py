import numpy as np
import json
from datetime import datetime
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
    
    print("=== Laptop GPS Receiver ===")
    print("Listening for rover GPS coordinates...")
    print("Bit 0 = 50 kHz, Bit 1 = 150 kHz")
    print("Press Ctrl+C to stop\n")
    
    # Pattern to search for: {"type":"gps"
    search_pattern = '{"type":"gps"'
    pattern_bits = string_to_bits(search_pattern)
    pattern_len = len(pattern_bits)
    
    last_message = None
    
    try:
        while True:
            iq = sdr.receive_samples()
            
            # Demodulate
            bits = fsk_demodulate(iq, sps=100, sample_rate=config["rx"]["sample_rate"])
            
            print(f"Demodulated {len(bits)} bits", end=" - ")
            
            # Search for GPS JSON pattern in the bitstream
            best_match = 0
            best_start = None
            
            for start in range(len(bits) - pattern_len):
                test_bits = bits[start:start+pattern_len]
                
                # Count how many bits match
                matches = np.sum(test_bits == pattern_bits)
                
                if matches > best_match:
                    best_match = matches
                    best_start = start
                
                # If we get a good match (>85%), likely found it
                if matches >= int(pattern_len * 0.85):
                    # Try to decode the full JSON (assume ~80 chars max)
                    message_bits = bits[start:start+640]  # 80 chars * 8 bits
                    message = bits_to_string(message_bits)
                    
                    # Find the end of JSON (closing brace)
                    if '}' in message:
                        json_str = message[:message.index('}')+1]
                        
                        try:
                            # Parse JSON
                            data = json.loads(json_str)
                            
                            # Display nicely
                            timestamp = datetime.fromtimestamp(data['t']).strftime('%Y-%m-%d %H:%M:%S')
                            
                            print("\n" + "=" * 50)
                            print(f"   GPS UPDATE - {timestamp}")
                            print(f"   Latitude:  {data['lat']:.6f}°")
                            print(f"   Longitude: {data['lon']:.6f}°")
                            if 'alt' in data:
                                print(f"   Altitude:  {data['alt']:.1f} m")
                            print(f"   Match quality: {matches}/{pattern_len} bits ({100*matches/pattern_len:.1f}%)")
                            print("=" * 50)
                            print("\nGPS coordinates received successfully!")
                            try:
                                sdr.close()
                            except:
                                pass
                            return
                            
                        except (json.JSONDecodeError, KeyError) as e:
                            print(f"Parse error: {e}")
            else:
                print(f"No GPS found (best match: {best_match}/{pattern_len} = {100*best_match/pattern_len:.1f}%)")
            
    except KeyboardInterrupt:
        print("\nStopping receiver...")
    finally:
        try:
            sdr.close()
        except:
            pass

if __name__ == "__main__":
    main()