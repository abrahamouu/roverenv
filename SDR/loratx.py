#!/usr/bin/env python3
"""
LoRa Transmitter using ADALM Pluto SDR
Sends LoRa packets to communicate with SX1276 base station
"""

from gnuradio import gr, blocks
try:
    from gnuradio import iio
except ImportError:
    print("ERROR: gr-iio not found. Install with: sudo apt install gr-iio")
    exit(1)

try:
    import lora
except ImportError:
    print("ERROR: gr-lora not found. Make sure it's installed properly.")
    exit(1)

import numpy as np
import time
import json
import pmt

class LoRaTransmitter(gr.top_block):
    def __init__(self, config_file="config.json"):
        gr.top_block.__init__(self, "LoRa Transmitter via Pluto SDR")
        
        # Load configuration
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        
        print("\n" + "="*60)
        print("    LoRa Transmitter - ADALM Pluto SDR")
        print("="*60)
        print(f"Frequency:     {self.config['tx']['frequency']/1e6:.1f} MHz")
        print(f"Sample Rate:   {self.config['tx']['sample_rate']/1e6:.1f} MSPS")
        print(f"LoRa BW:       {self.config['lora']['bandwidth']/1e3:.0f} kHz")
        print(f"Spreading:     SF{self.config['lora']['spreading_factor']}")
        print(f"Coding Rate:   4/{self.config['lora']['coding_rate']}")
        print("="*60 + "\n")
        
        # Message source - sends periodic messages
        self.message_strobe = blocks.message_strobe(
            pmt.intern("Hello from Rover!"),
            2000  # Send every 2000 ms (2 seconds)
        )
        
        # LoRa Encoder - encodes messages into LoRa packets
        self.lora_encoder = lora.lora_encode(
            spreading_factor=self.config['lora']['spreading_factor'],
            code_rate=self.config['lora']['coding_rate'],
            low_data_rate=False,
            header=not self.config['lora']['implicit_header']
        )
        
        # LoRa Modulator - generates LoRa chirps
        self.lora_modulator = lora.lora_mod(
            spreading_factor=self.config['lora']['spreading_factor'],
            bandwidth=self.config['lora']['bandwidth'],
            sample_rate=self.config['tx']['sample_rate']
        )
        
        # Pluto Sink - transmits via Pluto SDR
        self.pluto_sink = iio.pluto_sink(
            uri=self.config['connection']['uri'],
            frequency=int(self.config['tx']['frequency']),
            samplerate=int(self.config['tx']['sample_rate']),
            bandwidth=int(self.config['tx']['bandwidth']),
            buffer_size=self.config['tx']['buffer_size'],
            cyclic=False,
            attenuation1=int(abs(self.config['tx']['gain']) * 1000),  # Convert to mdB
            filter_auto=True
        )
        
        # Connect the blocks
        # Message flow: strobe -> encoder -> modulator -> pluto
        self.msg_connect((self.message_strobe, 'strobe'), 
                        (self.lora_encoder, 'in'))
        self.msg_connect((self.lora_encoder, 'out'), 
                        (self.lora_modulator, 'in'))
        self.connect((self.lora_modulator, 0), 
                    (self.pluto_sink, 0))

    def send_message(self, message):
        """Send a custom message via LoRa"""
        # Convert string to PMT (PolyMorphic Type for GNU Radio messages)
        msg_pmt = pmt.intern(str(message))
        # Post the message to the message strobe
        self.message_strobe.set_msg(msg_pmt)
        print(f"Queued message: {message}")


def main():
    print("Initializing LoRa Transmitter...")
    
    try:
        tb = LoRaTransmitter(config_file="config.json")
    except FileNotFoundError:
        print("\nERROR: config.json not found!")
        print("Please make sure the configuration file exists.")
        return
    except Exception as e:
        print(f"\nERROR: Failed to initialize transmitter: {e}")
        return
    
    try:
        print("Starting transmission...")
        print("Sending 'Hello from Rover!' every 2 seconds")
        print("Press Ctrl+C to stop\n")
        
        tb.start()
        
        # Keep running and allow user interaction
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nStopping transmitter...")
    except Exception as e:
        print(f"\nERROR during transmission: {e}")
    finally:
        tb.stop()
        tb.wait()
        print("Transmitter stopped.")


if __name__ == '__main__':
    main()