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

## Configuration

### Initial Setup

1. Go to Home Assistant Settings > Devices & Services. Your device may be automatically discovered. If so, you can skip steps 2-4 and go straight to step 5.
2. Click "+ Add Integration"
3. Search for "Philips Airfryer"
4. Enter the following required information:
   - **IP Address**: The local IP address of your airfryer (e.g., `192.168.0.123`)
5. Enter your **Client ID** and **Client Secret**. See below for the steps on how to get these.

### How to Get Client ID and Client Secret

You need to extract the Client ID and Client Secret from your Philips NutriU app. Here are the general steps:

#### Method 1: Network intercept
1. Use a network monitoring tool (like Charles Proxy or Wireshark) while using the NutriU app
2. Look for API calls to your airfryer. There should be an API call to www.backend.vbs.versuni.com
/api/`UUID`/Profile/self/Appliance containing JSON including `clientId` and `clientSecret`. These values are base64-encoded strings

For detailed instructions, see [this community discussion](https://community.home-assistant.io/t/philips-airfryer-nutriu-integration-alexa-only/544333/15).


#### Method 2: Android app database
1. Create a bootstick with Android x86 and boot from it or install it in Proxmox. It seems to be important that Android x86 and the Airfryer are in the same network & subnet. Installing Android x86 in for example VMware might work, but seems to have some problems. *Ignore this step if you have a rooted Android phone or tablet.*
2. Install NutriU and update Chrome (I recommend using Google Play Store and updating everything)
3. Install SQLite Database Editor: https://play.google.com/store/apps/details?id=com.tomminosoftware.sqliteeditor
4. Open SQLite Database Editor and allow Root for it (if that doesn't work Root might need to be enabled in Android 86 Developer Settings)
5. In the SQLite Database Editor select NutriU > network_node.db > network_node
6. The second last two columns are the ones we are interested in (swipe left to get there)

(Thank you @noxhirsch for the [second method](https://github.com/noxhirsch/Pyscript-Philips-Airfryer/blob/main/README.md))

### Troubleshooting

#### Network timeout or sensors having "unknown" state
The Air Fryer is very specific in how it handles network requests. It expects the connection to remain open. Sometimes it gets in a "locked" state (you can see this yourself by going to http://YOUR_AIRFRYER_IP_ADDRESS/upnp/description.xml, the page will fail to load).

When this happens, just unplug the airfryer and plug it back in. 

#### Updates don't come through for a while
The default polling interval is 60 seconds (once a minute). You can change this via advanced options. I would discourage you from polling too often, as this increases the likelyhood of the air fryer becoming "stuck" (see the previous troubleshooting item).
  
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
  - Default: `60` seconds
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
