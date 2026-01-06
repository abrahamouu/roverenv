"""
Configuration file for navigation system.
All tunable parameters in one place for easy experimentation.
"""

# ===== ERROR BOUNDS =====
POSITION_EPSILON = 2.0  # meters - arrival threshold (tune based on GPS accuracy)
GPS_ERROR_BASELINE = 2.5  # meters - NEO-6M typical accuracy

# ===== SENSOR REFRESH RATES =====
IMU_FREQUENCY = 100  # Hz - TUNE THIS through trial and error
MAG_FREQUENCY = 10   # Hz - magnetometer typically slower
GPS_RECHECK_INTERVAL = 30  # seconds - how often to recalibrate with GPS

# ===== IMU INTEGRATION PARAMETERS =====
ACCEL_BIAS = [0.0, 0.0, 0.0]  # m/s² - calibrated accelerometer bias (x, y, z)
VELOCITY_DECAY = 0.995  # Factor to combat velocity drift (1.0 = no decay)
POSITION_DECAY = 0.9995  # Factor to combat position drift

# ===== MAGNETOMETER PARAMETERS =====
MAG_DECLINATION = 0.0  # degrees - magnetic declination for your location
MAG_INTERFERENCE_THRESHOLD = 50.0  # μT - detect abnormal magnetic fields

# ===== MAGNETOMETER CALIBRATION =====
# Run: python magnetometer.py calibrate
MAG_OFFSET = [0.0, 0.0, 0.0]  # Hard iron offset [mx, my, mz]
MAG_SCALE = [1.0, 1.0, 1.0]   # Soft iron scale [mx, my, mz]

# ===== DRIFT COMPENSATION =====
HEADING_CORRECTION_ENABLED = True  # Use magnetometer to zero heading drift
VELOCITY_RESET_THRESHOLD = 0.05  # m/s - zero velocity if below this (stationary detection)

# ===== GPS RECALIBRATION =====
DRIFT_THRESHOLD = 5.0  # meters - force GPS recalibration if drift exceeds this
MIN_SATELLITES = 4  # Minimum satellites for reliable GPS fix
MAX_GPS_ERROR = 10.0  # meters - reject GPS fixes worse than this

# ===== COORDINATE SYSTEM =====
# Define which IMU axes map to North/East/Down
IMU_FORWARD_AXIS = 0  # 0=x, 1=y, 2=z
IMU_RIGHT_AXIS = 1
IMU_DOWN_AXIS = 2

# ===== LOGGING/DEBUG =====
ENABLE_DEBUG_LOGGING = True
LOG_FREQUENCY = 1  # Hz - how often to print debug info