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

def find_preamble(bits):
    """Find alternating 1010... pattern (64 bits)"""
    for start_pos in range(min(200, len(bits) - 64)):
        segment = bits[start_pos:start_pos+64]
        transitions = np.sum(segment[:-1] != segment[1:])
        
        # Need at least 50 transitions out of 63
        if transitions >= 50:
            return start_pos + 64  # Return position after preamble
    
    return None

def bits_to_bytes(bits):
    """Convert bits to bytes"""
    bytes_data = []
    for i in range(0, len(bits), 8):
        if i + 8 > len(bits):
            break
        byte_bits = bits[i:i+8]
        byte_val = 0
        for j, bit in enumerate(byte_bits):
            byte_val |= (bit << (7-j))
        bytes_data.append(byte_val)
    
    return bytes(bytes_data)

def decode_packet(bits):
    """Decode packet: find preamble, read length, extract data"""
    # Find preamble
    data_start = find_preamble(bits)
    
    if data_start is None:
        return None
    
    # Read length header (16 bits)
    if data_start + 16 > len(bits):
        return None
    
    length_bits = bits[data_start:data_start+16]
    length = 0
    for i, bit in enumerate(length_bits):
        length |= (int(bit) << (15-i))
    
    # Sanity check - prevent overflow
    if length > 500 or length == 0:
        return None
    
    # Calculate end position safely
    data_bit_start = data_start + 16
    data_bits_needed = length * 8
    
    # Check we have enough bits
    if data_bit_start + data_bits_needed > len(bits):
        return None
    
    data_bits = bits[data_bit_start:data_bit_start + data_bits_needed]
    data_bytes = bits_to_bytes(data_bits)
    
    try:
        message = data_bytes.decode('utf-8')
        return message
    except:
        return None

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
    print("Press Ctrl+C to stop\n")
    
    last_message = None
    
    try:
        while True:
            # Receive samples
            iq = sdr.receive_samples()
            
            # Demodulate
            bits = fsk_demodulate(iq, sps=100, sample_rate=config["rx"]["sample_rate"])
            
            # Decode packet
            message = decode_packet(bits)
            
            if message and message != last_message:
                last_message = message
                
                try:
                    # Parse JSON
                    data = json.loads(message)
                    
                    # Display nicely
                    timestamp = datetime.fromtimestamp(data['t']).strftime('%Y-%m-%d %H:%M:%S')
                    
                    print("=" * 50)
                    print(f"📍 GPS UPDATE - {timestamp}")
                    print(f"   Latitude:  {data['lat']:.6f}°")
                    print(f"   Longitude: {data['lon']:.6f}°")
                    if 'alt' in data:
                        print(f"   Altitude:  {data['alt']:.1f} m")
                    print("=" * 50)
                    print()
                    
                except json.JSONDecodeError:
                    print(f"Received (not JSON): {message}")
                except KeyError as e:
                    print(f"Missing field in GPS data: {e}")
            
    except KeyboardInterrupt:
        print("\nStopping receiver...")
    finally:
        sdr.close()

if __name__ == "__main__":
    main()