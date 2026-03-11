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