# config.py
"""
Configuration parameters for rover navigation system.
Tune these values through testing and trial/error.
"""

# ========================== SENSOR FREQUENCIES ========================== #
IMU_FREQUENCY = 50          # Hz
GPS_UPDATE_INTERVAL = 9999    # seconds — how often to correct position from GPS

# ========================== NAVIGATION THRESHOLDS ========================== #
POSITION_EPSILON = 0.5      # meters — "close enough" to destination
HEADING_TOLERANCE = 15      # degrees — heading error before correcting course
MIN_MOVE_DISTANCE = 0.3     # meters — minimum distance before moving
ESTIMATED_SPEED = 0.28  # m/s — tune this to match your rover's actual speed

# ========================== IMU FILTERING ========================== #
# Stationary noise threshold — any accel magnitude below this is treated as zero.
# To calibrate: read accel when rover is completely still, take the magnitude
# (sqrt(ax^2 + ay^2)) and set this slightly above the max you observe.
ACCEL_NOISE_THRESHOLD = 0.2    # m/s² — tune this first

# Velocity cap — clamps velocity to prevent runaway from bad IMU readings
MAX_VELOCITY = 1.5              # m/s — should be faster than your rover can actually go

# ========================== DRIFT COMPENSATION ========================== #
HEADING_CORRECTION_GAIN = 0.1   # 0.0-1.0, higher = more aggressive
VELOCITY_DECAY_FACTOR = 0.98    # was 0.98 — more aggressive decay prevents drift buildup
                                 # raise toward 0.99 if rover stops too soon

# GPS correction blend weight — higher = trust GPS more on resync
GPS_RESET_THRESHOLD = 5.0       # meters — if IMU drift exceeds this, force GPS resync

# ========================== MOTOR CONTROL ========================== #
BASE_SPEED = 0.6
TURN_SPEED = 1.0
MIN_SPEED = 0.2
HEADING_KP = 0.02

# ========================== SENSOR ADDRESSES ========================== #
IMU_I2C_ADDRESS = 0x68

# GPS Configuration
USE_IP_GEOLOCATION = False
USE_GPSD = True
IP_GEO_API_URL = "http://ip-api.com/json/"

# ========================== CALIBRATION VALUES ========================== #
# Magnetometer hard iron offset
MAG_OFFSET_X = 0.0
MAG_OFFSET_Y = 0.0
MAG_OFFSET_Z = 0.0

# Accelerometer bias — measure with rover flat and still (see README)
ACCEL_BIAS_X = 0.1615      # update with your measured value
ACCEL_BIAS_Y = -0.1051      # update with your measured value

# Gyro bias
GYRO_BIAS_X = 0.0
GYRO_BIAS_Y = 0.0
GYRO_BIAS_Z = 0.0

# Magnetic declination — Rancho Santa Margarita, CA
MAGNETIC_DECLINATION = 12.5

# ========================== COORDINATE SYSTEM ========================== #
REF_LAT = None
REF_LON = None

# ========================== DEBUG FLAGS ========================== #
DEBUG_PRINT_SENSORS = False
DEBUG_PRINT_NAVIGATION = True
DEBUG_PRINT_MOTORS = False