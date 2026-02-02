"""
SX1276 LoRa Base Station - Receiver (Simplified for Transparent Mode)
Receives LoRa messages from Rover (Pluto SDR)

Windows COM Port: COM4
Pre-configured Gowoops module in transparent mode
"""

import serial
import time
import sys


class SX1276BaseStation:
    def __init__(self, port='COM4', baudrate=9600):
        """Initialize SX1276 LoRa module"""
        print("\n" + "="*60)
        print("    SX1276 LoRa Base Station - Receiver")
        print("="*60)
        
        try:
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=1,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            print(f"Connected to SX1276 on {port} at {baudrate} baud")
            print("Module configured in transparent mode")
            print("Frequency: 915 MHz (pre-configured)")
            time.sleep(1)
            
        except serial.SerialException as e:
            print(f"ERROR: Could not open {port}")
            print(f"   {e}")
            sys.exit(1)
    
    def receive_continuous(self):
        """Continuously listen for incoming LoRa messages"""
        print("\n" + "="*60)
        print("LISTENING FOR LORA MESSAGES FROM ROVER")
        print("="*60)
        print("Press Ctrl+C to stop\n")
        
        message_count = 0
        raw_count = 0
        
        try:
            while True:
                if self.ser.in_waiting > 0:
                    raw_bytes = self.ser.read(self.ser.in_waiting)
                    
                    if raw_bytes:
                        raw_count += 1
                        timestamp = time.strftime("%H:%M:%S")
                        
                        # Try to decode as text
                        try:
                            data = raw_bytes.decode('utf-8', errors='ignore').strip()
                            if data:
                                message_count += 1
                                print(f"[{timestamp}] Message #{message_count}: {data}")
                        except:
                            pass
                        
                        # Show raw hex
                        hex_str = ' '.join([f'{b:02X}' for b in raw_bytes[:32]])
                        if len(raw_bytes) > 32:
                            hex_str += f" ... ({len(raw_bytes)} bytes)"
                        print(f"[{timestamp}] RAW #{raw_count}: {hex_str}")
                
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print("\n\nStopped listening")
            print(f"Messages: {message_count} | Raw packets: {raw_count}")
    
    def close(self):
        """Close serial connection"""
        if self.ser.is_open:
            self.ser.close()
            print("Serial port closed")


def main():
    print("\n" + "="*70)
    print("        SX1276 LoRa Base Station - Rover Communication")
    print("="*70)
    
    base = SX1276BaseStation(port='COM4', baudrate=9600)
    
    try:
        base.receive_continuous()
    finally:
        base.close()


if __name__ == "__main__":
    try:
        import serial
    except ImportError:
        print("\nERROR: pyserial not installed!")
        print("Install it with: pip install pyserial")
        sys.exit(1)
    
    main()