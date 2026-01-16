import iio
import numpy as np
import json


def load_config(config_file="config.json"):
    """Load configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        print(f"Loaded configuration from {config_file}")
        return config
    except FileNotFoundError:
        print(f"Config file '{config_file}' not found!")
        raise
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in config file: {e}")
        raise


class PlutoSDR:
    def __init__(self, uri="ip:192.168.2.1"):
        """Initialize connection to ADALM Pluto SDR"""
        try:
            self.ctx = iio.Context(uri)
            self.phy = self.ctx.find_device("ad9361-phy")
            self.rx = self.ctx.find_device("cf-ad9361-lpc")
            self.tx = self.ctx.find_device("cf-ad9361-dds-core-lpc")
            print(f"Connected to Pluto SDR at {uri}")
        except OSError as e:
            print(f"Failed to connect to Pluto SDR at {uri}")
            print(f"  Error: {e}")
            raise
    
    def set_rx_frequency(self, freq_hz):
        self.phy.find_channel("altvoltage0", True).attrs["frequency"].value = str(int(freq_hz))  
    
    def set_tx_frequency(self, freq_hz):
        self.phy.find_channel("altvoltage1", True).attrs["frequency"].value = str(int(freq_hz))

    def set_rx_bandwidth(self, bw_hz):
        self.phy.find_channel("voltage0").attrs["rf_bandwidth"].value = str(int(bw_hz))
    
    def set_tx_bandwidth(self, bw_hz):
        self.phy.find_channel("voltage0", True).attrs["rf_bandwidth"].value = str(int(bw_hz))
    
    # SAMPLING RATE FOR RX DETERMINED BY TX, SAME VALUES FOR BOTH
    def set_rx_sample_rate(self, rate):
        self.phy.find_channel("voltage0").attrs["sampling_frequency"].value = str(int(rate))
    
    def set_tx_sample_rate(self, rate):
        self.phy.find_channel("voltage0", True).attrs["sampling_frequency"].value = str(int(rate))
    
    def set_rx_gain_mode(self, mode):
        self.phy.find_channel("voltage0").attrs["gain_control_mode"].value = mode
    
    def set_rx_gain(self, gain_db):
        self.phy.find_channel("voltage0").attrs["hardwaregain"].value = str(gain_db)
    
    def set_tx_gain(self, gain_db):
        self.phy.find_channel("voltage0", True).attrs["hardwaregain"].value = str(gain_db)
        
    def get_rx_parameters(self):
        rx_chan = self.phy.find_channel("voltage0")     
        rx_lo = self.phy.find_channel("altvoltage0", True)
        
        return {
            "frequency": rx_lo.attrs["frequency"].value,
            "sample_rate": rx_chan.attrs["sampling_frequency"].value,
            "bandwidth": rx_chan.attrs["rf_bandwidth"].value,
            "gain_mode": rx_chan.attrs["gain_control_mode"].value,
            "gain": rx_chan.attrs["hardwaregain"].value
        }
    
    def get_tx_parameters(self):
        tx_chan = self.phy.find_channel("voltage0", True)
        tx_lo = self.phy.find_channel("altvoltage1", True)
        
        return {
            "frequency": tx_lo.attrs["frequency"].value,
            "sample_rate": tx_chan.attrs["sampling_frequency"].value,
            "bandwidth": tx_chan.attrs["rf_bandwidth"].value,
            "gain": tx_chan.attrs["hardwaregain"].value
        }
    
    def setup_rx_buffer(self, buffer_size=1024):
        self.rx_chan_i = self.rx.find_channel("voltage0")   # I channel
        self.rx_chan_q = self.rx.find_channel("voltage1")   # Q channel
        self.rx_chan_i.enabled = True
        self.rx_chan_q.enabled = True
        self.rx_buf = iio.Buffer(self.rx, buffer_size)
    
    def receive_samples(self):
        self.rx_buf.refill()
        i_data = np.frombuffer(self.rx_buf.read(), dtype=np.int16)[::2]
        q_data = np.frombuffer(self.rx_buf.read(), dtype=np.int16)[1::2]
        return i_data + 1j * q_data
        
    def setup_tx_buffer(self, buffer_size=1024):
        self.tx_chan_i = self.tx.find_channel("voltage0", True)
        self.tx_chan_q = self.tx.find_channel("voltage1", True)
        self.tx_chan_i.enabled = True
        self.tx_chan_q.enabled = True
        self.tx_buf = iio.Buffer(self.tx, buffer_size, cyclic=True)
    
    def transmit_samples(self, samples):
        i_data = np.real(samples).astype(np.int16)
        q_data = np.imag(samples).astype(np.int16)
        iq_interleaved = np.empty(len(samples) * 2, dtype=np.int16)
        iq_interleaved[::2] = i_data
        iq_interleaved[1::2] = q_data
        self.tx_buf.write(bytearray(iq_interleaved))
        self.tx_buf.push()
        
    def close(self):
        del self.ctx

    def explore_devices(self):
        print("=" * 80)
        print("ADALM PLUTO SDR DEVICES")
        print("=" * 80)
        for device in self.ctx.devices:
            print(f"  • {device.name}")


# test portion
if __name__ == "__main__":
    config = load_config("config.json")
    
    try:
        sdr = PlutoSDR(uri=config["connection"]["uri"])
    except OSError:
        print("\nCould not connect. Exiting.")
        exit(1)

    if config["operation"]["explore_devices"]:
        sdr.explore_devices()
    
    print("\n" + "="*60)
    print("\t\t\tCONFIGURING PLUTO SDR")
    print("="*60)
    
    sdr.set_rx_frequency(config["rx"]["frequency"])
    sdr.set_rx_sample_rate(config["rx"]["sample_rate"])
    sdr.set_rx_bandwidth(config["rx"]["bandwidth"])
    sdr.set_rx_gain_mode(config["rx"]["gain_mode"])

    # if mode is manual apply gain value
    if config["rx"]["gain_mode"] == "manual":
        sdr.set_rx_gain(config["rx"]["gain"])
    
    sdr.set_tx_frequency(config["tx"]["frequency"])
    sdr.set_tx_sample_rate(config["tx"]["sample_rate"])
    sdr.set_tx_bandwidth(config["tx"]["bandwidth"])
    sdr.set_tx_gain(config["tx"]["gain"])
    
    print("\nRX Parameters:")
    for key, value in sdr.get_rx_parameters().items():
        print(f"  {key}: {value}")
    
    print("\nTX Parameters:")
    for key, value in sdr.get_tx_parameters().items():
        print(f"  {key}: {value}")
    
    # testing RX/TX path and buffer/sampling
    if config["operation"]["receive_samples"]:
        sdr.setup_rx_buffer(config["rx"]["buffer_size"])
        print("\nReceiving samples...")
        samples = sdr.receive_samples()
        print(f"Received {len(samples)} complex samples")
        print(f"Sample range: {np.min(np.abs(samples)):.2f} to {np.max(np.abs(samples)):.2f}")
    
    if config["operation"]["transmit_tone"] and config["tone_generator"]["enabled"]:
        print("\nTransmitting tone...")
        sdr.setup_tx_buffer(config["tx"]["buffer_size"])
        t = np.arange(config["tx"]["buffer_size"]) / config["tx"]["sample_rate"]
        tone = config["tone_generator"]["amplitude"] * np.exp(2j * np.pi * config["tone_generator"]["frequency"] * t) * (2**14)
        sdr.transmit_samples(tone)
    
    sdr.close()
    print("\nDone!")