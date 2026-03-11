
# ========================== SENSOR FREQUENCIES ========================== #
IMU_FREQUENCY = 50          # Hz
GPS_UPDATE_INTERVAL = 9999    # seconds — how often to correct position from GPS

# ========================== NAVIGATION THRESHOLDS ========================== #
POSITION_EPSILON = 0.5      # meters
HEADING_TOLERANCE = 15      # degrees — heading error
MIN_MOVE_DISTANCE = 0.3     # meters — minimum distance before moving
ESTIMATED_SPEED = 0.28  # rover's actual speed

# ========================== IMU FILTERING ========================== #
ACCEL_NOISE_THRESHOLD = 0.2    # m/s² — tune this first
MAX_VELOCITY = 1.5       

# ========================== DRIFT COMPENSATION ========================== #
HEADING_CORRECTION_GAIN = 0.1   
VELOCITY_DECAY_FACTOR = 0.98    
GPS_RESET_THRESHOLD = 5.0       # meters — if IMU drift exceeds this, force GPS resync

# ========================== MOTOR CONTROL ========================== #
BASE_SPEED = 0.6
TURN_SPEED = 1.0
MIN_SPEED = 0.2
HEADING_KP = 0.02

# ========================== SENSOR ADDRESSES ========================== #
IMU_I2C_ADDRESS = 0x68
USE_IP_GEOLOCATION = False
USE_GPSD = True
IP_GEO_API_URL = "http://ip-api.com/json/"

# ========================== CALIBRATION VALUES ========================== #
# Magnetometer hard iron offset
MAG_OFFSET_X = 0.0
MAG_OFFSET_Y = 0.0
MAG_OFFSET_Z = 0.0

ACCEL_BIAS_X = 0.1615   
ACCEL_BIAS_Y = -0.1051      

# Gyro bias
GYRO_BIAS_X = 0.0
GYRO_BIAS_Y = 0.0
GYRO_BIAS_Z = 0.0

MAGNETIC_DECLINATION = 12.5

# ========================== COORDINATE SYSTEM ========================== #
REF_LAT = None
REF_LON = None

# ========================== DEBUG FLAGS ========================== #
DEBUG_PRINT_SENSORS = False
DEBUG_PRINT_NAVIGATION = True
DEBUG_PRINT_MOTORS = False