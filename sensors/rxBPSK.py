import numpy as np
import time
from sdr_control import PlutoSDR, load_config

def main():
    config = load_config("config.json")
    sdr = PlutoSDR(uri=config["connection"]["uri"])

    # configure RX
    sdr.set_rx_frequency(config["rx"]["frequency"])
    sdr.set_rx_sample_rate(config["rx"]["sample_rate"])
    sdr.set_rx_bandwidth(config["rx"]["bandwidth"])
    sdr.set_rx_gain_mode("manual")
    sdr.set_rx_gain(60)  # high gain

    buf_size = 32768
    sdr.setup_rx_buffer(buf_size)
    
    print(f"Listening for signals...")
    print(f"Sample rate: {config['rx']['sample_rate']} Hz")
    print("Looking for peak at ~100 kHz offset")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            iq = sdr.receive_samples()
            
            # Compute FFT to see spectrum
            fft = np.fft.fftshift(np.fft.fft(iq))
            power = np.abs(fft)**2
            power_db = 10*np.log10(power + 1e-10)
            
            # Find peak
            peak_idx = np.argmax(power_db)
            peak_power = power_db[peak_idx]
            
            # Frequency of peak
            freqs = np.fft.fftshift(np.fft.fftfreq(len(iq), 1/config['rx']['sample_rate']))
            peak_freq = freqs[peak_idx]
            
            # Average power (noise floor)
            avg_power = np.mean(power_db)
            
            print(f"Peak: {peak_freq/1000:7.1f} kHz @ {peak_power:6.1f} dB | "
                  f"Noise floor: {avg_power:6.1f} dB | "
                  f"SNR: {peak_power - avg_power:5.1f} dB")
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        sdr.close()

if __name__ == "__main__":
    main()