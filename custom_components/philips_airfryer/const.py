"""Constants for the Philips Airfryer integration."""

DOMAIN = "philips_airfryer"

# Configuration keys
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_COMMAND_URL = "command_url"
CONF_AIRSPEED = "airspeed"
CONF_PROBE = "probe"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_REPLACE_TIMESTAMP = "replace_timestamp"
CONF_TIME_REMAINING = "time_remaining"
CONF_TIME_TOTAL = "time_total"
CONF_MAC_ADDRESS = "mac_address"

# Default values
DEFAULT_COMMAND_URL = "/di/v1/products/1/airfryer"
DEFAULT_AIRSPEED = False
DEFAULT_PROBE = False
DEFAULT_UPDATE_INTERVAL = 60
DEFAULT_REPLACE_TIMESTAMP = False
DEFAULT_TIME_REMAINING = "disp_time"
DEFAULT_TIME_TOTAL = "total_time"
DEFAULT_SLEEP_TIME = 0.1

# Service names
SERVICE_TURN_ON = "turn_on"
SERVICE_TURN_OFF = "turn_off"
SERVICE_START_COOKING = "start_cooking"
SERVICE_ADJUST_TIME = "adjust_time"
SERVICE_ADJUST_TEMP = "adjust_temp"
SERVICE_TOGGLE_AIRSPEED = "toggle_airspeed"
SERVICE_PAUSE = "pause"
SERVICE_START_RESUME = "start_resume"
SERVICE_STOP = "stop"

# Sensor keys
SENSOR_STATUS = "status"
SENSOR_TEMP = "temp"
SENSOR_TIMESTAMP = "timestamp"
SENSOR_TOTAL_TIME = "total_time"
SENSOR_DISP_TIME = "disp_time"
SENSOR_PROGRESS = "progress"
SENSOR_DRAWER_OPEN = "drawer_open"
SENSOR_DIALOG = "dialog"
SENSOR_AIRSPEED = "airspeed"
SENSOR_TEMP_PROBE = "temp_probe"
SENSOR_PROBE_UNPLUGGED = "probe_unplugged"
