# data_logger.py
"""
Log sensor data and navigation state to CSV for analysis.
"""
import csv
import time
from datetime import datetime
import config

_log_file = None
_csv_writer = None
_start_time = None

def init_logger(filename=None):
    """
    Initialize CSV logger.
    Creates file with headers.
    """
    global _log_file, _csv_writer, _start_time
    
    if not config.LOG_ENABLED:
        print("Logging disabled in config")
        return
    
    if filename is None:
        filename = config.LOG_FILE
    
    _start_time = time.time()
    _log_file = open(filename, 'w', newline='')
    _csv_writer = csv.writer(_log_file)
    
    # Write header
    _csv_writer.writerow([
        'timestamp',        # seconds since start
        'datetime',         # human readable
        'lat',              # GPS latitude
        'lon',              # GPS longitude
        'x_calc',           # Calculated X position (meters)
        'y_calc',           # Calculated Y position (meters)
        'vx',               # Velocity X (m/s)
        'vy',               # Velocity Y (m/s)
        'ax_body',          # Accel X body frame (m/s²)
        'ay_body',          # Accel Y body frame (m/s²)
        'az_body',          # Accel Z body frame (m/s²)
        'ax_earth',         # Accel X earth frame (m/s²)
        'ay_earth',         # Accel Y earth frame (m/s²)
        'heading',          # Magnetometer heading (degrees)
        'target_bearing',   # Bearing to destination (degrees)
        'heading_error',    # Heading error (degrees)
        'distance_to_dest', # Distance to destination (meters)
        'motor_command'     # Motor command (forward/turn_left/etc)
    ])
    
    print(f"Data logger initialized: {filename}")

def log_data(lat=None, lon=None, x_calc=None, y_calc=None, 
             vx=None, vy=None, ax_body=None, ay_body=None, az_body=None,
             ax_earth=None, ay_earth=None, heading=None, 
             target_bearing=None, heading_error=None, 
             distance_to_dest=None, motor_command=None):
    """
    Log a data point. Pass None for unavailable values.
    """
    global _csv_writer, _start_time
    
    if not config.LOG_ENABLED or _csv_writer is None:
        return
    
    timestamp = time.time() - _start_time
    dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    _csv_writer.writerow([
        f'{timestamp:.3f}',
        dt,
        lat,
        lon,
        f'{x_calc:.3f}' if x_calc is not None else '',
        f'{y_calc:.3f}' if y_calc is not None else '',
        f'{vx:.3f}' if vx is not None else '',
        f'{vy:.3f}' if vy is not None else '',
        f'{ax_body:.3f}' if ax_body is not None else '',
        f'{ay_body:.3f}' if ay_body is not None else '',
        f'{az_body:.3f}' if az_body is not None else '',
        f'{ax_earth:.3f}' if ax_earth is not None else '',
        f'{ay_earth:.3f}' if ay_earth is not None else '',
        f'{heading:.1f}' if heading is not None else '',
        f'{target_bearing:.1f}' if target_bearing is not None else '',
        f'{heading_error:.1f}' if heading_error is not None else '',
        f'{distance_to_dest:.3f}' if distance_to_dest is not None else '',
        motor_command if motor_command is not None else ''
    ])

def flush():
    """Force write to disk (call periodically or after important events)."""
    if _log_file:
        _log_file.flush()

def close_logger():
    """Close log file cleanly."""
    global _log_file, _csv_writer
    
    if _log_file:
        _log_file.close()
        print("Data logger closed")
        _log_file = None
        _csv_writer = None

# Test mode
if __name__ == "__main__":
    print("Testing data logger...")
    
    # Temporarily enable logging for test
    config.LOG_ENABLED = True
    config.LOG_FILE = "test_log.csv"
    
    init_logger()
    
    # Log some fake data points
    for i in range(5):
        log_data(
            lat=33.6189 + i*0.00001,
            lon=-117.6142 + i*0.00001,
            x_calc=i * 1.5,
            y_calc=i * 2.0,
            vx=0.5,
            vy=0.3,
            ax_body=0.1,
            ay_body=0.05,
            az_body=9.81,
            heading=45.0,
            target_bearing=60.0,
            heading_error=15.0,
            distance_to_dest=50.0 - i*10,
            motor_command='forward'
        )
        time.sleep(0.1)
    
    close_logger()
    print("Test complete. Check test_log.csv")