# import numpy as np
# import time
# import json
# from sdr_control import PlutoSDR, load_config

# def get_gps_data():
#     """
#     Get GPS coordinates - replace this with actual GPS module later
#     For now, returns hardcoded coordinates with current timestamp
#     """
#     payload = {
#         "type": "gps",
#         "lat": 34.0689,
#         "lon": -118.4452,
#         "alt": 100.5,
#         "t": int(time.time())
#     }
#     return json.dumps(payload)

# def string_to_bits(text):
#     """Convert string to bits"""
#     bits = []
#     for char in text:
#         byte = ord(char)
#         for i in range(8):
#             bits.append((byte >> (7-i)) & 1)
#     return np.array(bits, dtype=np.uint8)

# def fsk_modulate(bits, sps=100, sample_rate=4000000):
#     """
#     FSK: bit 0 = 50kHz tone, bit 1 = 150kHz tone
#     """
#     freq_0 = 50000   # 50 kHz for bit 0
#     freq_1 = 150000  # 150 kHz for bit 1
    
#     samples_per_bit = sps
#     t_bit = np.arange(samples_per_bit) / sample_rate
    
#     signal = []
#     for bit in bits:
#         freq = freq_1 if bit == 1 else freq_0
#         tone = np.exp(2j * np.pi * freq * t_bit)
#         signal.extend(tone)
    
#     iq = np.array(signal, dtype=np.complex64)
#     iq *= 0.8 * (2**14)
    
#     return iq

# def main():
#     config = load_config("config.json")
#     sdr = PlutoSDR(uri=config["connection"]["uri"])

#     sdr.set_tx_frequency(config["tx"]["frequency"])
#     sdr.set_tx_sample_rate(config["tx"]["sample_rate"])
#     sdr.set_tx_bandwidth(config["tx"]["bandwidth"])
#     sdr.set_tx_gain(0)

#     print("=== Rover GPS Transmitter ===")
#     print("Transmitting GPS coordinates every 2 seconds")
#     print("Bit 0 = 50 kHz, Bit 1 = 150 kHz")
#     print("Press Ctrl+C to stop\n")
    
#     # Setup buffer once with max size we'll need
#     # GPS JSON is ~80 chars = 640 bits + 64 preamble = 704 bits
#     # x3 repeats = 2112 bits x 100 sps = 211,200 samples
#     max_samples = 220000
#     sdr.setup_tx_buffer(max_samples)
#     print(f"Buffer size: {max_samples} samples\n")
    
#     try:
#         while True:
#             # Get fresh GPS data
#             gps_json = get_gps_data()
            
#             print(f"Sending: {gps_json}")
            
#             # Preamble: alternating bits (same as BPSK)
#             preamble_bits = np.tile([1, 0], 32)  # 64 bits
#             data_bits = string_to_bits(gps_json)
            
#             # Send multiple copies (same as BPSK)
#             packet = np.concatenate([preamble_bits, data_bits])
#             all_bits = np.tile(packet, 3)
            
#             iq = fsk_modulate(all_bits, sps=100, sample_rate=config["tx"]["sample_rate"])
            
#             # Pad to buffer size
#             if len(iq) < max_samples:
#                 padding = np.zeros(max_samples - len(iq), dtype=np.complex64)
#                 iq = np.concatenate([iq, padding])
            
#             print(f"Total samples: {len(iq)}")
            
#             # Transmit
#             sdr.transmit_samples(iq)
            
#             print(f"Transmitted!\n")
            
#             # Wait before next transmission
#             time.sleep(2)
            
#     except KeyboardInterrupt:
#         print("\nStopping transmitter...")
#     finally:
#         sdr.close()

# if __name__ == "__main__":
#     main()

import numpy as np
import time
import json
from gps_test import get_current_gps

def get_gps_data():
    # payload = {
    #     "type": "gps",
    #     "lat": 34.0689,
    #     "lon": -118.4452,
    #     "alt": 100.5,
    #     "t": int(time.time())
    # }
    # return json.dumps(payload)
    data = get_current_gps()

    if not data["has_fix"]:
        print("No GPS fix — skipping TX")
        return None

    payload = {
        "type": "gps",
        "lat": data["lat"],
        "lon": data["lon"],
        "t": int(time.time())
    }

    return json.dumps(payload)


def string_to_bits(text):
    bits = []
    for char in text:
        byte = ord(char)
        for i in range(8):
            bits.append((byte >> (7 - i)) & 1)
    return np.array(bits, dtype=np.uint8)


def fsk_modulate(bits, sps=100, sample_rate=4_000_000):
    freq_0 = 50000
    freq_1 = 150000

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


def transmit_once(sdr):

    print("=== Rover GPS TX (Endpoint Triggered) ===")

    gps_json = get_gps_data()
    print(f"Sending: {gps_json}")

    preamble_bits = np.tile([1, 0], 32)
    data_bits = string_to_bits(gps_json)

    packet = np.concatenate([preamble_bits, data_bits])
    all_bits = np.tile(packet, 3)

    tx_params = sdr.get_tx_parameters()
    sample_rate = float(tx_params["sample_rate"])

    iq = fsk_modulate(all_bits, sps=100, sample_rate=sample_rate)

    max_samples = 220000

    if len(iq) < max_samples:
        padding = np.zeros(max_samples - len(iq), dtype=np.complex64)
        iq = np.concatenate([iq, padding])

 
    if not hasattr(sdr, "tx_buf"):
        print("Setting up TX buffer...")
        sdr.setup_tx_buffer(max_samples)

    print(f"Total samples: {len(iq)}")

    for _ in range(5):
        sdr.transmit_samples(iq)
        time.sleep(0.05)

    print("Transmitted bursts!\n")