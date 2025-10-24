# NOAA Tides Integration for Home Assistant

A Home Assistant custom integration that provides real-time tide information from NOAA (National Oceanic and Atmospheric Administration) tide stations.

## Features

- **Current Tide Height**: Real-time water level measurements in meters
- **Tide Trend**: Shows whether the tide is rising, falling, or steady with rate in ft/hr
- **Next High Tide**: Time and height of the next high tide
- **Next Low Tide**: Time and height of the next low tide
- **Beautiful Tide Chart**: SVG chart showing tide predictions with configurable time ranges (6-168 hours)
- **Custom Prediction Sensors**: Create sensors for any time offset (e.g., "15min", "1h", "-30min" for historical)
- **Automatic Station Discovery**: Find nearby stations by ZIP code
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

## Advanced Features

### Tide Chart

The integration provides a beautiful SVG tide chart as an **Image Entity**:
- **Smooth curves** using cubic spline interpolation
- **Configurable time ranges**: 6-168 hours of future predictions
- **Historical data**: 0-168 hours of past tide data
- **High/Low markers**: Clearly marked on the chart with heights
- **Current time indicator**: Orange line showing "now"
- **Timezone-aware**: Uses your Home Assistant configured timezone
- **Dark theme optimized**: Looks great in any dashboard

**Configuration options:**
- `Chart Hours`: How many hours ahead to display (default: 24)
- `Chart History Hours`: How many hours back to display (default: 0)

### Custom Prediction Sensors

Create sensors for tide height at any time offset:

**Examples:**
- `15min` - Tide height 15 minutes from now
- `1h` - Tide height in 1 hour
- `2.5h` - Tide height in 2.5 hours
- `-30min` - Tide height 30 minutes ago (historical)
- `-1h` - Tide height 1 hour ago
- `1d` - Tide height in 1 day

**Supported formats:**
- Minutes: `15`, `15m`, `15min`, `15mins`, `15minutes`
- Hours: `1h`, `1hr`, `1hour`, `2.5h`
- Days: `1d`, `1day`, `2days`
- Negative values for historical data: `-15min`, `-1h`

Each custom sensor shows:
- Predicted tide height in meters
- Exact prediction time
- Time interval configured

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

### Dashboard: Display Tide Chart

Add the tide chart image to your dashboard:

```yaml
type: picture-entity
entity: image.noaa_tides_tide_chart
show_name: true
show_state: false
```

Or in a card with sensors:

```yaml
type: vertical-stack
cards:
  - type: picture-entity
    entity: image.noaa_tides_tide_chart
    show_name: false
    show_state: false
  - type: entities
    entities:
      - entity: sensor.noaa_tides_current_tide_height
      - entity: sensor.noaa_tides_tide_trend
      - entity: sensor.noaa_tides_next_high_tide
      - entity: sensor.noaa_tides_next_low_tide
```

### Automation: Notify Before High Tide

```yaml
automation:
  - alias: "High Tide Alert"
    trigger:
      - platform: state
        entity_id: sensor.noaa_tides_next_high_tide
    condition:
      - condition: template
        value_template: >
          {{ (as_timestamp(states('sensor.noaa_tides_next_high_tide')) - as_timestamp(now())) < 1800 }}
    action:
      - service: notify.mobile_app
        data:
          title: "High Tide Soon!"
          message: "High tide in 30 minutes: {{ state_attr('sensor.noaa_tides_next_high_tide', 'height') }}m"
```

### Automation: Using Custom Prediction Sensors

Alert when tide will be high enough for kayaking in 2 hours:

```yaml
automation:
  - alias: "Kayaking Tide Check"
    trigger:
      - platform: time_pattern
        hours: "/1"  # Check every hour
    condition:
      - condition: numeric_state
        entity_id: sensor.noaa_tides_tide_height_2h
        above: 1.5  # Minimum depth needed
    action:
      - service: notify.mobile_app
        data:
          message: "Good tide for kayaking in 2 hours!"
```

### Template: Time Until Next High Tide

```yaml
sensor:
  - platform: template
    sensors:
      time_until_high_tide:
        friendly_name: "Time Until High Tide"
        value_template: >
          {% set high_tide = states('sensor.noaa_tides_next_high_tide') | as_datetime %}
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
