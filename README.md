# NOAA Tides Integration for Home Assistant

A Home Assistant custom integration that provides real-time tide information from NOAA (National Oceanic and Atmospheric Administration) tide stations.

## Features

- **Current Tide Height**: Real-time water level measurements in meters
- **Tide Trend**: Shows whether the tide is rising, falling, or steady
- **Next High Tide**: Time and height of the next high tide
- **Next Low Tide**: Time and height of the next low tide
- **Device Integration**: Each tide station appears as a device with multiple sensors
- **HACS Compatible**: Easy installation and updates through HACS

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add the repository URL: `https://github.com/andyleap/noaa_tides`
5. Select category: "Integration"
6. Click "Add"
7. Search for "NOAA Tides" and install it
8. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/noaa_tides` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "NOAA Tides"
4. Enter your ZIP code
5. Select the nearest tide station from the list
6. (Optional) Configure prediction intervals and chart settings

### Station Discovery

The integration automatically finds tide stations near you:
- Enter any US ZIP code
- Displays the 10 nearest NOAA tide stations
- Shows distance from your location
- Indicates which stations have live water level data vs predictions-only
- Lists station details (name, state, ID)

Example stations that may appear:
- `8454000` - Providence, RI
- `8518750` - The Battery, NY
- `9414290` - San Francisco, CA
- `9447130` - Seattle, WA

## Sensors

Each configured tide station creates a device with the following sensors:

### Current Tide Height
- **Unit**: Meters (MLLW datum)
- **Updates**: Every 10 minutes
- **Icon**: Wave icon
- **Attributes**: Last update time

### Tide Trend
- **Values**: rising, falling, or steady
- **Icon**: Changes based on trend (arrow up/down/horizontal)
- **Updates**: Every 10 minutes

### Next High Tide
- **Type**: Timestamp
- **Icon**: Arrow up
- **Attributes**: Height in meters
- **Updates**: Every 10 minutes

### Next Low Tide
- **Type**: Timestamp
- **Icon**: Arrow down
- **Attributes**: Height in meters
- **Updates**: Every 10 minutes

## Usage Examples

### Automation: Notify Before High Tide

```yaml
automation:
  - alias: "High Tide Alert"
    trigger:
      - platform: time
        at: "{{ state_attr('sensor.my_station_next_high_tide', 'timestamp') - timedelta(hours=1) }}"
    action:
      - service: notify.mobile_app
        data:
          message: "High tide in 1 hour: {{ state_attr('sensor.my_station_next_high_tide', 'height') }}m"
```

### Template: Time Until Next High Tide

```yaml
sensor:
  - platform: template
    sensors:
      time_until_high_tide:
        friendly_name: "Time Until High Tide"
        value_template: >
          {% set high_tide = states('sensor.my_station_next_high_tide') | as_datetime %}
          {% set diff = high_tide - now() %}
          {{ diff.total_seconds() // 3600 }}h {{ (diff.total_seconds() % 3600) // 60 }}m
```

## API Rate Limiting

This integration queries the NOAA API every 10 minutes. NOAA does not publish official rate limits, but this integration is designed to be respectful of their resources.

## Troubleshooting

### "Could not connect to this station"
- Verify the station ID is correct
- Check that the station provides water level data (not all NOAA stations do)
- Ensure your Home Assistant instance has internet access

### Data Not Updating
- Check the Home Assistant logs for errors
- Verify the NOAA API is accessible: https://api.tidesandcurrents.noaa.gov/
- Try reloading the integration

## Support

For issues, feature requests, or contributions, please visit:
https://github.com/andyleap/noaatides/issues

## License

This project is licensed under the MIT License.

## Credits

Data provided by NOAA's Center for Operational Oceanographic Products and Services.
