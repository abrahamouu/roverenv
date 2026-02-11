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
    Convert IQ samples to bits with matched filtering and timing recovery
    """
    # apply matched filter
    rrc = raised_cosine_filter(beta=0.35, span=10, sps=sps)
    filtered = np.convolve(iq_samples, rrc, mode='same')
    
    # Simple timing recovery: find best sampling phase by maximizing signal energy
    best_phase = 0
    max_energy = 0
    
    for phase in range(sps):
        samples = filtered[phase::sps].real
        energy = np.sum(samples**2)
        if energy > max_energy:
            max_energy = energy
            best_phase = phase
    
    # downsample at best phase
    symbols = filtered[best_phase::sps].real
    
    # decision
    bits = (symbols > 0).astype(int)
    return bits, best_phase

def find_preamble_correlation(bits, threshold=0.5):
    """
    Find preamble using correlation - detects polarity inversion
    """
    barker13 = np.array([1,1,1,1,1,0,0,1,1,0,1,0,1])
    preamble = np.tile(barker13, 10)  # 130 bits
    
    # convert to -1/+1 for correlation
    preamble_bipolar = 2*preamble - 1
    bits_bipolar = 2*bits - 1
    
    # correlate
    corr = np.correlate(bits_bipolar, preamble_bipolar, mode='valid')
    corr_norm = corr / len(preamble)
    
    # find peak (positive or negative) above threshold
    max_corr = np.max(np.abs(corr_norm))
    peaks = np.where(np.abs(corr_norm) > threshold * max_corr)[0]
    
    if len(peaks) > 0:
        best_peak = peaks[np.argmax(np.abs(corr_norm[peaks]))]
        idx = best_peak + len(preamble)  # end of preamble
        
        # Check if we need to invert (negative correlation)
        inverted = corr_norm[best_peak] < 0
        
        print(f"Preamble at {idx}, corr: {corr_norm[best_peak]:.2f}, inverted: {inverted}")
        return idx, inverted
    
    return None, False

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
    result = find_preamble_correlation(bits, threshold=0.5)
    if result[0] is None:
        return None
    
    idx, inverted = result
    
    # If signal is inverted, flip all bits
    if inverted:
        bits = 1 - bits
        print("Signal inverted - flipping bits")
    
    # sanity check: enough bits for length header?
    if idx + 16 > len(bits):
        print(f"Not enough bits for header. Have {len(bits)}, need {idx+16}")
        return None
        
    # get length header (16 bits)
    length_bits = bits[idx:idx+16]
    print(f"Length header bits: {length_bits[:16]}")
    length_bytes = np.packbits(length_bits).tobytes()
    packet_len = int.from_bytes(length_bytes, "little")
    
    print(f"Decoded length: {packet_len} bytes")
    
    # sanity check packet length
    if packet_len > 1024 or packet_len == 0:
        print(f"Invalid packet length: {packet_len}")
        return None
    
    # extract repeated payload bits (3x repetition)
    payload_bits_repeated_len = packet_len * 8 * 3
    if idx + 16 + payload_bits_repeated_len > len(bits):
        print(f"Not enough bits for payload. Have {len(bits)}, need {idx+16+payload_bits_repeated_len}")
        return None
        
    payload_bits_repeated = bits[idx+16: idx+16 + payload_bits_repeated_len]
    
    # decode using majority voting
    payload_bits = majority_decode(payload_bits_repeated, rep_factor=3)
    
    payload_bytes = bits_to_bytes(payload_bits)
    
    print(f"Decoded bytes (hex): {payload_bytes.hex()[:60]}...")

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
    
    # Calculate actual samples per symbol based on sample rate
    # TX uses: symbol_rate = sample_rate / sps = 4MHz / 40 = 100k symbols/sec
    symbol_rate = 100000  # 100 kHz symbol rate (from TX)
    actual_sps = int(config["rx"]["sample_rate"] / symbol_rate)
    print(f"Using {actual_sps} samples per symbol (sample rate: {config['rx']['sample_rate']} Hz)")

    print("Waiting for packets...")

    try:
        while True:
            iq = sdr.receive_samples()
            bits, phase = bpsk_demodulate(iq, sps=actual_sps)
            packet = decode_packet(bits)
            if packet:
                print(f"✓ Received packet (phase={phase}):", packet)

    except KeyboardInterrupt:
        print("Stopping RX...")

    finally:
        sdr.close()

if __name__ == "__main__":
    main()