import numpy as np
import json
from sdr_control import PlutoSDR, load_config

def bits_to_bytes(bits):
    bits = np.array(bits, dtype=np.uint8)
    # pad to multiple of 8
    extra = 8 - (len(bits) % 8)
    if extra != 8:
        bits = np.concatenate([bits, np.zeros(extra, dtype=np.uint8)])
    return np.packbits(bits).tobytes()

def bpsk_demodulate(iq_samples, sps=40):
    """
    Convert IQ samples to bits
    """
    # downsample to symbol rate by taking one sample per symbol
    symbols = iq_samples[::sps].real
    bits = (symbols > 0).astype(int)
    return bits

def find_preamble(bits, preamble=np.tile([1, 0], 64)):
    """
    Find preamble index in bitstream
    """
    for i in range(len(bits) - len(preamble)):
        if np.array_equal(bits[i:i+len(preamble)], preamble):
            return i + len(preamble)
    return None

def decode_packet(bits):
    """
    Extract packet after preamble
    """
    preamble_len = 128
    idx = find_preamble(bits)
    if idx is None:
        return None

    # get length header (16 bits)
    length_bits = bits[idx:idx+16]
    length_bytes = bits_to_bytes(length_bits)
    packet_len = int.from_bytes(length_bytes, "little")

    # extract payload bits
    payload_bits = bits[idx+16: idx+16 + packet_len*8]
    payload_bytes = bits_to_bytes(payload_bits)

    try:
        return json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        print(f"Failed to decode JSON: {e}")
        return None

def main():
    config = load_config("config.json")

    sdr = PlutoSDR(uri=config["connection"]["uri"])

    # configure RX
    sdr.set_rx_frequency(config["rx"]["frequency"])
    sdr.set_rx_sample_rate(config["rx"]["sample_rate"])
    sdr.set_rx_bandwidth(config["rx"]["bandwidth"])
    sdr.set_rx_gain_mode(config["rx"]["gain_mode"])

    # manual gain if needed
    if config["rx"]["gain_mode"] == "manual":
        sdr.set_rx_gain(config["rx"]["gain"])

    # setup buffer
    buf_size = config["rx"]["buffer_size"]
    sdr.setup_rx_buffer(buf_size)

    print("Waiting for packets...")

    try:
        while True:
            iq = sdr.receive_samples()
            bits = bpsk_demodulate(iq, sps=40)
            packet = decode_packet(bits)
            if packet:
                print("Received packet:", packet)

    except KeyboardInterrupt:
        print("Stopping RX...")

    finally:
        sdr.close()

if __name__ == "__main__":
    main()
