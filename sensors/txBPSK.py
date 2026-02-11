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

    # stronger preamble: Barker-13 sequence repeated (better autocorrelation)
    barker13 = np.array([1,1,1,1,1,0,0,1,1,0,1,0,1])
    preamble = np.tile(barker13, 10)  # 130 bits
    
    # length header (2 bytes, explicit little-endian)
    length_bytes = np.array([len(data)], dtype=np.uint16).tobytes()
    length_bits = np.unpackbits(np.frombuffer(length_bytes, dtype=np.uint8))
    
    # simple repetition code: repeat each data bit 3 times for error correction
    bits_repeated = np.repeat(bits, 3)

    return np.concatenate([preamble, length_bits, bits_repeated])

def raised_cosine_filter(beta=0.35, span=10, sps=40):
    """Root raised cosine filter for pulse shaping"""
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

def bpsk_modulate(bits, sps=40, amplitude=0.6):
    """
    bits -> BPSK IQ waveform with matched filtering
    sps = samples per symbol
    """
    symbols = 2*bits - 1          # 0→-1, 1→+1
    upsampled = np.repeat(symbols, sps)

    # apply matched filter for better noise immunity
    rrc = raised_cosine_filter(beta=0.35, span=10, sps=sps)
    filtered = np.convolve(upsampled, rrc, mode='same')
    
    iq = filtered.astype(np.complex64)

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

    # build message ONCE (reuse same packet for testing)
    msg = build_payload()
    print("TX message:", msg)

    bits = build_packet_bits(msg)

    iq = bpsk_modulate(
        bits,
        sps=40,
        amplitude=0.9  # increased from 0.6 to 0.9 for stronger signal
    )

    print("TX samples:", len(iq))

    # setup buffer large enough
    sdr.setup_tx_buffer(len(iq))

    print("Starting continuous transmission (Ctrl+C to stop)...")
    
    try:
        while True:
            sdr.transmit_samples(iq)
            print(".", end="", flush=True)  # show it's transmitting
            time.sleep(0.5)  # small delay between transmissions
            
    except KeyboardInterrupt:
        print("\nStopping transmitter...")
    finally:
        sdr.close()

if __name__ == "__main__":
    main()