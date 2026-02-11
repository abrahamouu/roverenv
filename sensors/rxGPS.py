import numpy as np
import json
from datetime import datetime
from sdr_control import PlutoSDR, load_config

def fsk_demodulate(iq_samples, sps=100, sample_rate=4000000):
    """
    Improved FSK demod using energy detection in frequency bins
    More robust than per-bit FFT
    """
    num_bits = len(iq_samples) // sps
    bits = []
    
    # Pre-compute frequency bins for 50kHz and 150kHz
    bin_50k = int(50000 * sps / sample_rate)
    bin_150k = int(150000 * sps / sample_rate)
    
    for i in range(num_bits):
        segment = iq_samples[i*sps:(i+1)*sps]
        
        # Compute FFT
        fft = np.fft.fft(segment)
        power = np.abs(fft) ** 2
        
        # Check energy around 50kHz and 150kHz
        # Look at a few bins around each frequency
        energy_50k = np.sum(power[max(0, bin_50k-2):bin_50k+3])
        energy_150k = np.sum(power[max(0, bin_150k-2):bin_150k+3])
        
        # Decide based on which has more energy
        bits.append(1 if energy_150k > energy_50k else 0)
    
    return np.array(bits, dtype=np.uint8)

def find_preamble(bits):
    """Find alternating 1010... pattern (128 bits now)"""
    preamble_len = 128
    
    for start_pos in range(min(500, len(bits) - preamble_len)):
        segment = bits[start_pos:start_pos+preamble_len]
        transitions = np.sum(segment[:-1] != segment[1:])
        
        # Need at least 100 transitions out of 127 (more lenient)
        if transitions >= 100:
            return start_pos + preamble_len  # Return position after preamble
    
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
    """Decode packet: find preamble, read length, extract data, verify checksum"""
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
    
    # Sanity check
    if length > 500 or length == 0:
        return None
    
    # Calculate positions
    data_bit_start = data_start + 16
    data_bits_needed = length * 8
    checksum_start = data_bit_start + data_bits_needed
    
    # Check we have enough bits (data + 8 bit checksum)
    if checksum_start + 8 > len(bits):
        return None
    
    # Extract data bits and checksum bits
    data_bits = bits[data_bit_start:data_bit_start + data_bits_needed]
    checksum_bits = bits[checksum_start:checksum_start + 8]
    
    # Convert to bytes
    data_bytes = bits_to_bytes(data_bits)
    
    # Calculate expected checksum
    expected_checksum = 0
    for byte in data_bytes:
        expected_checksum ^= byte
    
    # Get received checksum
    received_checksum = 0
    for i, bit in enumerate(checksum_bits):
        received_checksum |= (int(bit) << (7-i))
    
    # Verify checksum
    if expected_checksum != received_checksum:
        print(f"Checksum mismatch: expected {expected_checksum}, got {received_checksum}")
        # Still try to decode, but warn user
    
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

    # Larger buffer to capture full transmission
    sdr.setup_rx_buffer(262144)
    
    print("=== Laptop GPS Receiver ===")
    print("Listening for rover GPS coordinates...")
    print("Press Ctrl+C to stop\n")
    
    last_message = None
    consecutive_fails = 0
    
    try:
        while True:
            # Receive samples
            iq = sdr.receive_samples()
            
            # Demodulate
            bits = fsk_demodulate(iq, sps=100, sample_rate=config["rx"]["sample_rate"])
            
            print(f"Demodulated {len(bits)} bits", end=" - ")
            
            # Decode packet
            message = decode_packet(bits)
            
            if message:
                consecutive_fails = 0
                
                if message != last_message:
                    last_message = message
                    
                    try:
                        # Parse JSON
                        data = json.loads(message)
                        
                        # Display nicely
                        timestamp = datetime.fromtimestamp(data['t']).strftime('%Y-%m-%d %H:%M:%S')
                        
                        print("\n" + "=" * 50)
                        print(f"📍 GPS UPDATE - {timestamp}")
                        print(f"   Latitude:  {data['lat']:.6f}°")
                        print(f"   Longitude: {data['lon']:.6f}°")
                        if 'alt' in data:
                            print(f"   Altitude:  {data['alt']:.1f} m")
                        print("=" * 50)
                        print()
                        
                    except json.JSONDecodeError:
                        print(f"\nReceived (not JSON): {message}\n")
                    except KeyError as e:
                        print(f"\nMissing field in GPS data: {e}\n")
                else:
                    print("(duplicate)")
            else:
                consecutive_fails += 1
                print(f"No packet found (fail #{consecutive_fails})")
                
                # After 5 fails, suggest checking transmitter
                if consecutive_fails == 5:
                    print("\n*** No packets received in 5 attempts. Check:")
                    print("    1. Transmitter is running")
                    print("    2. Frequencies match in config.json")
                    print("    3. Gain settings\n")
            
    except KeyboardInterrupt:
        print("\nStopping receiver...")
    finally:
        sdr.close()

if __name__ == "__main__":
    main()