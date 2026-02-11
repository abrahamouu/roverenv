import numpy as np
import time
import json
from sdr_control import PlutoSDR, load_config

def get_gps_data():
    """
    Get GPS coordinates - replace this with actual GPS module later
    For now, returns hardcoded coordinates with current timestamp
    """
    payload = {
        "type": "gps",
        "lat": 34.0689,
        "lon": -118.4452,
        "alt": 100.5,  # altitude in meters
        "t": int(time.time())
    }
    return json.dumps(payload)

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

def build_packet(message):
    """Build packet with preamble + length + data"""
    # Preamble for sync
    preamble_bits = np.tile([1, 0], 32)  # 64 bits
    
    # Length header (2 bytes = 16 bits)
    length = len(message)
    length_bits = []
    for i in range(16):
        length_bits.append((length >> (15-i)) & 1)
    length_bits = np.array(length_bits, dtype=np.uint8)
    
    # Data
    data_bits = string_to_bits(message)
    
    # Combine: preamble + length + data
    packet = np.concatenate([preamble_bits, length_bits, data_bits])
    
    return packet

def main():
    config = load_config("config.json")
    sdr = PlutoSDR(uri=config["connection"]["uri"])

    sdr.set_tx_frequency(config["tx"]["frequency"])
    sdr.set_tx_sample_rate(config["tx"]["sample_rate"])
    sdr.set_tx_bandwidth(config["tx"]["bandwidth"])
    sdr.set_tx_gain(0)

    print("=== Rover GPS Transmitter ===")
    print("Transmitting GPS coordinates every 2 seconds")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Get fresh GPS data
            gps_json = get_gps_data()
            
            print(f"Sending: {gps_json}")
            
            # Build packet
            packet_bits = build_packet(gps_json)
            
            # Repeat packet 3 times for reliability
            all_bits = np.tile(packet_bits, 3)
            
            # Modulate
            iq = fsk_modulate(all_bits, sps=100, sample_rate=config["tx"]["sample_rate"])
            
            # Transmit
            sdr.setup_tx_buffer(len(iq))
            sdr.transmit_samples(iq)
            
            print(f"Transmitted {len(packet_bits)} bits ({len(iq)} samples)\n")
            
            # Wait before next transmission
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nStopping transmitter...")
    finally:
        sdr.close()

if __name__ == "__main__":
    main()