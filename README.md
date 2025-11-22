# Philips Airfryer Home Assistant Integration

A Home Assistant custom integration for Philips connected airfryers with full GUI configuration support via HACS.

## Features

- Full GUI configuration through Home Assistant's integration setup
- Real-time monitoring of airfryer status, temperature, time remaining, and progress
- Control services for turning on/off, starting cooking, adjusting time/temperature, and more
- Support for advanced models with airspeed control (HD9880/90)
- Support for temperature probe (HD9880/90 & HD9875/90)
- Local polling - works entirely on your local network
- HACS compatible for easy installation and updates

## Installation

### HACS (Recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed in your Home Assistant
2. Add this repository as a custom repository in HACS:
   - Go to HACS > Integrations
   - Click the three dots in the top right corner
   - Select "Custom repositories"
   - Add URL: `https://github.com/b12e/hacs_philips_airfryer`
   - Category: Integration
3. Click "Explore & Download Repositories"
4. Search for "Philips Airfryer"
5. Click "Download"
6. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/philips_airfryer` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

### Initial Setup

1. Go to Home Assistant Settings > Devices & Services
2. Click "+ Add Integration"
3. Search for "Philips Airfryer"
4. Enter the following required information:
   - **IP Address**: The local IP address of your airfryer (e.g., `192.168.0.123`)
   - **Client ID**: Your airfryer's client ID (base64 encoded string)
   - **Client Secret**: Your airfryer's client secret (base64 encoded string)

### How to Get Client ID and Client Secret

You need to extract the Client ID and Client Secret from your Philips NutriU app. Here are the general steps:

1. Use a network monitoring tool (like Charles Proxy or Wireshark) while using the NutriU app
2. Look for API calls to your airfryer
3. Extract the `client_id` and `client_secret` from the authentication headers
4. These values are base64-encoded strings

For detailed instructions, see [this community discussion](https://community.home-assistant.io/t/philips-airfryer-nutriu-integration-alexa-only/544333/15).

Alternatively, follow these instructions:
1. Create a bootstick with Android x86 and boot from it or install it in Proxmox. It seems to be important that Android x86 and the Airfryer are in the same network & subnet. Installing Android x86 in for example VMware might work, but seems to have some problems. *Ignore this step if you have a rooted Android phone or tablet.*
2. Install NutriU and update Chrome (I recommend using Google Play Store and updating everything)
3. Install SQLite Database Editor: https://play.google.com/store/apps/details?id=com.tomminosoftware.sqliteeditor
4. Open SQLite Database Editor and allow Root for it (if that doesn't work Root might need to be enabled in Android 86 Developer Settings)
5. In the SQLite Database Editor select NutriU > network_node.db > network_node
6. The second last two columns are the ones we are interested in (swipe left to get there)

(Thank you @noxhirsch for the [instructions](https://github.com/noxhirsch/Pyscript-Philips-Airfryer/blob/main/README.md))

### Advanced Options

After initial setup, you can configure advanced options:

1. Go to Home Assistant Settings > Devices & Services
2. Find your Philips Airfryer integration
3. Click "Configure"

Available options:

- **Command URL**: Set to `/di/v1/products/1/venusaf` for some devices (HD9880/90)
  - Default: `/di/v1/products/1/airfryer`
- **Enable Airspeed**: Enable for HD9880/90 models with dual fan speed
  - Default: `False`
- **Enable Temperature Probe**: Enable for HD9880/90 & HD9875/90 with temperature probe
  - Default: `False`
- **Update Interval**: How often to poll the airfryer (in seconds)
  - Default: `20` seconds
- **Replace Timestamp**: Set to `True` if you block internet access for the airfryer
  - Default: `False`
- **Time Remaining Field**: Set to `cur_time` for HD9255 (Experimental)
  - Default: `disp_time`
- **Time Total Field**: Set to `time` for HD9255 (Experimental)
  - Default: `total_time`

## Entities

The integration creates the following sensors:

### Standard Sensors (All Models)

- **Status**: Current operational status (standby, precook, cooking, pause, finish, powersave, offline)
- **Temperature**: Target cooking temperature (°C)
- **Timestamp**: Timestamp of the current cooking session
- **Total Time**: Total cooking time set (seconds)
- **Time Remaining**: Time remaining in current cooking session (seconds)
- **Progress**: Cooking progress percentage (%)
- **Drawer Open**: Indicates if the drawer is open (boolean)
- **Dialog**: Current dialog/notification status

### Additional Sensors (HD9880/90 with airspeed enabled)

- **Airspeed**: Current fan speed setting (1 or 2)

### Additional Sensors (HD9880/90 & HD9875/90 with probe enabled)

- **Temperature Probe**: Current temperature probe reading (°C)
- **Probe Unplugged**: Indicates if the probe is unplugged (boolean)

## Services

The integration provides the following services:

### `philips_airfryer.turn_on`

Turns the airfryer on (into precook mode).

### `philips_airfryer.turn_off`

Turns the airfryer off (stops it first if needed).

### `philips_airfryer.start_cooking`

Turns the airfryer on, sets it up, and starts cooking.

**Parameters:**
- `temp` (optional): Cooking temperature (40-200°C, default: 180)
- `total_time` (optional): Cooking duration in seconds (60-86400, default: 60)
- `airspeed` (optional): Airspeed setting 1 or 2 (for compatible models, default: 2)
- `start_cooking` (optional): Whether to start cooking immediately (default: true)
- `force_update` (optional): Force sensor update before command (default: true)

**Example:**
```yaml
service: philips_airfryer.start_cooking
data:
  temp: 200
  total_time: 900  # 15 minutes
  airspeed: 2
```

### `philips_airfryer.adjust_time`

Adjust cooking time while in precook, pause, or cooking mode.

**Parameters:**
- `time` (required): Seconds to add or subtract (1-86400)
- `method` (required): `add` or `subtract`
- `restart_cooking` (optional): Whether to restart cooking if it was cooking before (default: true)
- `force_update` (optional): Force sensor update before command (default: true)

**Example:**
```yaml
service: philips_airfryer.adjust_time
data:
  time: 300  # Add 5 minutes
  method: add
```

### `philips_airfryer.adjust_temp`

Adjust cooking temperature while in precook, pause, or cooking mode.

**Parameters:**
- `temp` (required): Degrees to add or subtract (1-160°C)
- `method` (required): `add` or `subtract`
- `restart_cooking` (optional): Whether to restart cooking if it was cooking before (default: true)
- `force_update` (optional): Force sensor update before command (default: true)

**Example:**
```yaml
service: philips_airfryer.adjust_temp
data:
  temp: 10  # Increase by 10°C
  method: add
```

### `philips_airfryer.toggle_airspeed`

Toggles the airspeed between high (2) and low (1). Only available for compatible models.

### `philips_airfryer.pause`

Pauses the airfryer.

### `philips_airfryer.start_resume`

Starts the airfryer if everything is set up, or resumes if paused.

### `philips_airfryer.stop`

Stops the airfryer and returns to main menu.

## Example Automations

### Notification When Cooking Is Done

```yaml
automation:
  - alias: "Airfryer Cooking Done"
    trigger:
      - platform: state
        entity_id: sensor.philips_airfryer_status
        to: "finish"
    action:
      - service: notify.mobile_app
        data:
          message: "Your airfryer has finished cooking!"
```

### Start Cooking at Specific Time

```yaml
automation:
  - alias: "Start Airfryer for Dinner"
    trigger:
      - platform: time
        at: "18:00:00"
    action:
      - service: philips_airfryer.start_cooking
        data:
          temp: 180
          total_time: 1200  # 20 minutes
```

### Adjust Time Based on Drawer Opening

```yaml
automation:
  - alias: "Pause When Drawer Opens"
    trigger:
      - platform: state
        entity_id: sensor.philips_airfryer_drawer_open
        to: true
    condition:
      - condition: state
        entity_id: sensor.philips_airfryer_status
        state: "cooking"
    action:
      - service: philips_airfryer.pause
```

## Supported Devices

This integration has been tested with:

- HD9255 (with experimental settings)
- HD9875/90 (with probe support)
- HD9880/90 (with airspeed and probe support)
- Other Philips connected airfryers should work with the default settings

## Troubleshooting

### Connection Issues

- Verify the IP address is correct and the airfryer is on your local network
- Check that your Client ID and Client Secret are correct
- Ensure your airfryer is powered on
- Try adjusting the update interval if you're experiencing frequent disconnections

### Device-Specific Issues

- **HD9880/90**: Set Command URL to `/di/v1/products/1/venusaf` and enable Airspeed and Probe options
- **HD9255**: Set Time Remaining to `cur_time` and Time Total to `time` in the options
- **Offline devices**: Enable "Replace Timestamp" if you block internet access for the airfryer

### Debug Logging

Add this to your `configuration.yaml` to enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.philips_airfryer: debug
```

## Credits

Based on the original [pyscript implementation](https://github.com/noxhirsch/Pyscript-Philips-Airfryer/blob/main/README.md) and [Carsten T.'s findings on authentication]((https://community.home-assistant.io/t/philips-airfryer-nutriu-integration-alexa-only/544333/15)):

## License

MIT License

## Support

For issues, feature requests, or questions, please [open an issue on GitHub](https://github.com/b12e/hacs_philips_airfryer/issues).
