# config.py
"""
Configuration parameters for rover navigation system.
Tune these values through testing and trial/error.
"""

# ========================== SENSOR FREQUENCIES ========================== #
IMU_FREQUENCY = 50  # Hz - How often to read IMU (find through trial/error)
GPS_UPDATE_INTERVAL = 30  # seconds - How often to resync position with GPS
MAG_HEADING_UPDATE = 10  # Hz - How often to update heading from magnetometer

# ========================== NAVIGATION THRESHOLDS ========================== #
POSITION_EPSILON = 1.5  # meters - "Close enough" to destination
HEADING_TOLERANCE = 15  # degrees - Acceptable heading error before correcting
MIN_MOVE_DISTANCE = 0.5  # meters - Minimum distance before we start moving

# ========================== DRIFT COMPENSATION ========================== #
# Gains for correcting IMU drift using magnetometer
HEADING_CORRECTION_GAIN = 0.1  # 0.0-1.0, higher = more aggressive correction
VELOCITY_DECAY_FACTOR = 0.98  # Simulate friction/drag to prevent runaway velocity
GPS_RESET_THRESHOLD = 5.0  # meters - If IMU drift exceeds this, force GPS resync

# ========================== MOTOR CONTROL ========================== #
BASE_SPEED = 0.5  # Default motor speed (0.0-1.0)
TURN_SPEED = 0.3  # Speed when turning
MIN_SPEED = 0.2  # Minimum speed to overcome static friction

# Proportional control for heading correction
HEADING_KP = 0.02  # Proportional gain for heading error -> turn rate

# ========================== SENSOR ADDRESSES ========================== #
IMU_I2C_ADDRESS = 0x68  # MPU6050 default address

# GPS Configuration
USE_IP_GEOLOCATION = False  # Set to True to use IP geolocation instead of real GPS
USE_GPSD = True  # Use gpsd daemon for GPS

# IP Geolocation API (fallback when USE_IP_GEOLOCATION = True)
IP_GEO_API_URL = "http://ip-api.com/json/"

# Real GPS Module via gpsd
# Make sure gpsd is configured in /etc/default/gpsd with your GPS serial port

# ========================== DATA LOGGING ========================== #
LOG_ENABLED = True
LOG_FILE = "rover_navigation_log.csv"
LOG_FREQUENCY = 10  # Hz - How often to write to log file

# ========================== CALIBRATION VALUES ========================== #
# Magnetometer calibration (hard iron offset)
# TODO: Run calibration routine and update these values
MAG_OFFSET_X = 0.0
MAG_OFFSET_Y = 0.0
MAG_OFFSET_Z = 0.0

# Accelerometer bias (at rest, should read ~9.81 in z, 0 in x,y)
ACCEL_BIAS_X = 0.0
ACCEL_BIAS_Y = 0.0
ACCEL_BIAS_Z = 0.0

# Gyro bias (at rest, should read 0)
GYRO_BIAS_X = 0.0
GYRO_BIAS_Y = 0.0
GYRO_BIAS_Z = 0.0

# Magnetic declination for your location (degrees)
# Find yours at: https://www.ngdc.noaa.gov/geomag/calculators/magcalc.shtml
MAGNETIC_DECLINATION = 12.5  # Rancho Santa Margarita, CA approx

# ========================== COORDINATE SYSTEM ========================== #
# Reference point for local coordinate system (set from first GPS reading)
REF_LAT = None  # Will be set at runtime
REF_LON = None

# ========================== DEBUG FLAGS ========================== #
DEBUG_PRINT_SENSORS = False  # Print raw sensor values
DEBUG_PRINT_NAVIGATION = True  # Print navigation calculations
DEBUG_PRINT_MOTORS = False  # Print motor commands