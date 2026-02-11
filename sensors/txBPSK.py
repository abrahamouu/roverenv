import numpy as np
import time
from sdr_control import PlutoSDR, load_config

def main():
    config = load_config("config.json")
    sdr = PlutoSDR(uri=config["connection"]["uri"])

    # configure TX
    sdr.set_tx_frequency(config["tx"]["frequency"])
    sdr.set_tx_sample_rate(config["tx"]["sample_rate"])
    sdr.set_tx_bandwidth(config["tx"]["bandwidth"])
    sdr.set_tx_gain(0)  # use 0 dB gain

    # Generate simple continuous tone at 100 kHz offset
    sample_rate = config["tx"]["sample_rate"]
    tone_freq = 100000  # 100 kHz
    duration = 0.1  # 100ms bursts
    
    num_samples = int(sample_rate * duration)
    t = np.arange(num_samples) / sample_rate
    
    # Simple sine wave tone - VERY strong signal
    tone = np.exp(2j * np.pi * tone_freq * t).astype(np.complex64)
    tone *= 0.9 * (2**14)  # 90% of full scale
    
    sdr.setup_tx_buffer(len(tone))
    
    print(f"Transmitting 100 kHz tone continuously...")
    print(f"Sample rate: {sample_rate} Hz")
    print(f"Tone frequency: {tone_freq} Hz")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            sdr.transmit_samples(tone)
            print(".", end="", flush=True)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        sdr.close()

if __name__ == "__main__":
    main()