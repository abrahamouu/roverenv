import iio


def check_pluto_parameters(uri="ip:192.168.2.1"):
    """Check current Pluto SDR parameters"""
    
    try:
        ctx = iio.Context(uri)
        phy = ctx.find_device("ad9361-phy")
        print(f"Connected to Pluto SDR at {uri}\n")
    except OSError as e:
        print(f"Failed to connect: {e}")
        return
    
    # Get RX parameters
    rx_chan = phy.find_channel("voltage0")
    rx_lo = phy.find_channel("altvoltage0", True)
    
    print("="*60)
    print("\t\t\tRX PARAMETERS")
    print("="*60)
    print(f"Frequency      : {rx_lo.attrs['frequency'].value}")
    print(f"Sample Rate    : {rx_chan.attrs['sampling_frequency'].value}")
    print(f"Bandwidth      : {rx_chan.attrs['rf_bandwidth'].value}")
    print(f"Gain Mode      : {rx_chan.attrs['gain_control_mode'].value}")
    print(f"Gain           : {rx_chan.attrs['hardwaregain'].value}")
    
    # Get TX parameters
    tx_chan = phy.find_channel("voltage0", True)
    tx_lo = phy.find_channel("altvoltage1", True)
    
    print("\n" + "="*60)
    print("\t\t\tTX PARAMETERS")
    print("="*60)
    print(f"Frequency      : {tx_lo.attrs['frequency'].value}")
    print(f"Sample Rate    : {tx_chan.attrs['sampling_frequency'].value}")
    print(f"Bandwidth      : {tx_chan.attrs['rf_bandwidth'].value}")
    print(f"Gain           : {tx_chan.attrs['hardwaregain'].value}")
    
    del ctx


if __name__ == "__main__":
    check_pluto_parameters(uri="ip:192.168.2.1")
    print("\n" + "="*60)