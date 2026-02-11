import numpy as np
import json
from sdr_control import PlutoSDR, load_config

def bits_to_bytes(bits):
    bits = np.array(bits, dtype=np.uint8)
    # pad to multiple of 8 only if needed
    remainder = len(bits) % 8
    if remainder != 0:
        bits = np.pad(bits, (0, 8 - remainder), mode='constant')
    return np.packbits(bits).tobytes()

def raised_cosine_filter(beta=0.35, span=10, sps=40):
    """Root raised cosine matched filter (same as TX)"""
    t = np.arange(-span*sps//2, span*sps//2) / sps
    h = np.zeros(len(t))
    
    for i, ti in enumerate(t):
        if ti == 0:
            h[i] = (1 + beta*(4/np.pi - 1))
        elif abs(ti) == 1/(4*beta) and beta != 0:
            h[i] = (beta/np.sqrt(2)) * ((1+2/np.pi)*np.sin(np.pi/(4*beta)) + 
                                         (1-2/np.pi)*np.cos(np.pi/(4*beta)))
        else:
            h[i] = (np.sin(np.pi*ti*(1-beta)) + 4*beta*ti*np.cos(np.pi*ti*(1+beta))) / \
                   (np.pi*ti*(1-(4*beta*ti)**2))
    
    return h / np.sqrt(np.sum(h**2))

def bpsk_demodulate(iq_samples, sps=40):
    """
    Convert IQ samples to bits with matched filtering
    """
    # apply matched filter
    rrc = raised_cosine_filter(beta=0.35, span=10, sps=sps)
    filtered = np.convolve(iq_samples, rrc, mode='same')
    
    # downsample to symbol rate
    symbols = filtered[::sps].real
    
    # decision
    bits = (symbols > 0).astype(int)
    return bits

def find_preamble_correlation(bits, threshold=0.7):
    """
    Find preamble using correlation (more robust than exact match)
    """
    barker13 = np.array([1,1,1,1,1,0,0,1,1,0,1,0,1])
    preamble = np.tile(barker13, 10)  # 130 bits
    
    # convert to -1/+1 for correlation
    preamble_bipolar = 2*preamble - 1
    bits_bipolar = 2*bits - 1
    
    # correlate
    corr = np.correlate(bits_bipolar, preamble_bipolar, mode='valid')
    corr_norm = corr / len(preamble)
    
    # find peak above threshold
    peaks = np.where(corr_norm > threshold * np.max(corr_norm))[0]
    
    if len(peaks) > 0:
        idx = peaks[0] + len(preamble)  # end of preamble
        return idx
    return None

def majority_decode(bits_repeated, rep_factor=3):
    """
    Decode repetition code: take majority vote of each rep_factor bits
    """
    num_orig_bits = len(bits_repeated) // rep_factor
    decoded = np.zeros(num_orig_bits, dtype=np.uint8)
    
    for i in range(num_orig_bits):
        chunk = bits_repeated[i*rep_factor:(i+1)*rep_factor]
        decoded[i] = 1 if np.sum(chunk) > rep_factor/2 else 0
    
    return decoded

def decode_packet(bits):
    """
    Extract packet after preamble with error correction
    """
    idx = find_preamble_correlation(bits, threshold=0.7)
    if idx is None:
        return None
    
    # sanity check: enough bits for length header?
    if idx + 16 > len(bits):
        return None
        
    # get length header (16 bits)
    length_bits = bits[idx:idx+16]
    length_bytes = np.packbits(length_bits).tobytes()
    packet_len = int.from_bytes(length_bytes, "little")
    
    # sanity check packet length
    if packet_len > 1024 or packet_len == 0:
        return None
    
    # extract repeated payload bits (3x repetition)
    payload_bits_repeated_len = packet_len * 8 * 3
    if idx + 16 + payload_bits_repeated_len > len(bits):
        return None
        
    payload_bits_repeated = bits[idx+16: idx+16 + payload_bits_repeated_len]
    
    # decode using majority voting
    payload_bits = majority_decode(payload_bits_repeated, rep_factor=3)
    
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