import numpy as np
import json
import time
from sdr_control import PlutoSDR, load_config   # your file name here

# replace with GPS call later instead of hardcoded
def build_payload():
    payload = {
        "type": "gps",
        "lat": 34.0689,
        "lon": -118.4452,
        "t": int(time.time())
    }
    return json.dumps(payload)

def bytes_to_bits(data_bytes):
    return np.unpackbits(np.frombuffer(data_bytes, dtype=np.uint8))

def build_packet_bits(msg_str):
    data = msg_str.encode("utf-8")
    bits = bytes_to_bits(data)

    # preamble for sync
    preamble = np.tile([1, 0], 64)

    # length header (2 bytes)
    length_bits = np.unpackbits(
        np.array([len(data)], dtype=np.uint16).view(np.uint8)
    )

    return np.concatenate([preamble, length_bits, bits])

def bpsk_modulate(bits, sps=40, amplitude=0.6):
    """
    bits -> BPSK IQ waveform
    sps = samples per symbol
    """
    symbols = 2*bits - 1          # 0→-1, 1→+1
    upsampled = np.repeat(symbols, sps)

    iq = upsampled.astype(np.float32) + 0j

    # scale to Pluto DAC range
    iq *= amplitude * (2**14)

    return iq

def main():
    config = load_config("config.json")

    sdr = PlutoSDR(uri=config["connection"]["uri"])

    # configure from config.json
    sdr.set_tx_frequency(config["tx"]["frequency"])
    sdr.set_tx_sample_rate(config["tx"]["sample_rate"])
    sdr.set_tx_bandwidth(config["tx"]["bandwidth"])
    sdr.set_tx_gain(config["tx"]["gain"])

    # build message
    msg = build_payload()
    print("TX message:", msg)

    bits = build_packet_bits(msg)

    iq = bpsk_modulate(
        bits,
        sps=40,
        amplitude=0.6
    )

    print("TX samples:", len(iq))

    # setup buffer large enough
    sdr.setup_tx_buffer(len(iq))

    sdr.transmit_samples(iq)

    print("Transmission pushed")

    time.sleep(1)
    sdr.close()

if __name__ == "__main__":
    main()
