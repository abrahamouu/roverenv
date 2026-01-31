#!/usr/bin/env python3
"""
LoRa Receiver using ADALM Pluto SDR
Receives LoRa packets from SX1276 base station
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

import json
import pmt
import time


class MessagePrinter(gr.basic_block):
    """Custom block to print received LoRa messages"""
    def __init__(self):
        gr.basic_block.__init__(
            self,
            name="message_printer",
            in_sig=None,
            out_sig=None
        )
        self.message_port_register_in(pmt.intern('in'))
        self.set_msg_handler(pmt.intern('in'), self.handle_msg)
        self.msg_count = 0
    
    def handle_msg(self, msg):
        """Handle incoming LoRa messages"""
        try:
            # Convert PMT to string
            msg_str = pmt.symbol_to_string(msg)
            self.msg_count += 1
            
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] Message #{self.msg_count}: {msg_str}")
            
        except Exception as e:
            print(f"Error decoding message: {e}")


class LoRaReceiver(gr.top_block):
    def __init__(self, config_file="config_lora.json"):
        gr.top_block.__init__(self, "LoRa Receiver via Pluto SDR")
        
        # Load configuration
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        
        print("\n" + "="*60)
        print("    LoRa Receiver - ADALM Pluto SDR")
        print("="*60)
        print(f"Frequency:     {self.config['rx']['frequency']/1e6:.1f} MHz")
        print(f"Sample Rate:   {self.config['rx']['sample_rate']/1e6:.1f} MSPS")
        print(f"LoRa BW:       {self.config['lora']['bandwidth']/1e3:.0f} kHz")
        print(f"Spreading:     SF{self.config['lora']['spreading_factor']}")
        print(f"Coding Rate:   4/{self.config['lora']['coding_rate']}")
        print(f"RX Gain:       {self.config['rx']['gain']} dB")
        print("="*60 + "\n")
        
        # Pluto Source - receives via Pluto SDR
        self.pluto_source = iio.pluto_source(
            uri=self.config['connection']['uri'],
            frequency=int(self.config['rx']['frequency']),
            samplerate=int(self.config['rx']['sample_rate']),
            bandwidth=int(self.config['rx']['bandwidth']),
            buffer_size=self.config['rx']['buffer_size'],
            gain1=self.config['rx']['gain'] if self.config['rx']['gain_mode'] == 'manual' else 0,
            manual_gain=(self.config['rx']['gain_mode'] == 'manual'),
            filter_auto=True
        )
        
        # LoRa Demodulator - detects LoRa chirps and demodulates
        self.lora_demod = lora.lora_demod(
            spreading_factor=self.config['lora']['spreading_factor'],
            bandwidth=self.config['lora']['bandwidth'],
            sample_rate=self.config['rx']['sample_rate'],
            implicit_header=self.config['lora']['implicit_header'],
            reduced_rate=False
        )
        
        # LoRa Decoder - decodes LoRa packets back to messages
        self.lora_decoder = lora.lora_decode(
            spreading_factor=self.config['lora']['spreading_factor'],
            code_rate=self.config['lora']['coding_rate'],
            low_data_rate=False,
            header=not self.config['lora']['implicit_header']
        )
        
        # Custom message printer
        self.msg_printer = MessagePrinter()
        
        # Connect the blocks
        # Signal flow: pluto -> demodulator
        self.connect((self.pluto_source, 0), 
                    (self.lora_demod, 0))
        
        # Message flow: demodulator -> decoder -> printer
        self.msg_connect((self.lora_demod, 'out'), 
                        (self.lora_decoder, 'in'))
        self.msg_connect((self.lora_decoder, 'out'), 
                        (self.msg_printer, 'in'))


def main():
    print("Initializing LoRa Receiver...")
    
    try:
        tb = LoRaReceiver(config_file="config_lora.json")
    except FileNotFoundError:
        print("\nERROR: config_lora.json not found!")
        print("Please make sure the configuration file exists.")
        return
    except Exception as e:
        print(f"\nERROR: Failed to initialize receiver: {e}")
        return
    
    try:
        print("Starting receiver...")
        print("Listening for LoRa messages...")
        print("Press Ctrl+C to stop\n")
        
        tb.start()
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nStopping receiver...")
    except Exception as e:
        print(f"\nERROR during reception: {e}")
    finally:
        tb.stop()
        tb.wait()
        print("Receiver stopped.")


if __name__ == '__main__':
    main()