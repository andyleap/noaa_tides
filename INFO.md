# NOAA Tides

[![GitHub Release](https://img.shields.io/github/release/andyleap/noaa_tides.svg)](https://github.com/andyleap/noaa_tides/releases)
[![Validate](https://github.com/andyleap/noaa_tides/workflows/Validate/badge.svg)](https://github.com/andyleap/noaa_tides/actions)
[![HACS](https://img.shields.io/badge/HACS-Default-orange.svg)](https://hacs.xyz)

Real-time tide monitoring from NOAA tide stations for Home Assistant.

## Features

🌊 **Real-Time Tide Data**
- Current tide height with MLLW datum
- Tide trend (rising/falling) with rate in ft/hr
- Next high and low tide predictions

📊 **Beautiful Visualizations**
- SVG tide charts with smooth curves
- Configurable time ranges (6-168 hours)
- High/low tide markers
- Timezone-aware display

🎯 **Flexible Configuration**
- Automatic station discovery by ZIP code
- Custom prediction intervals (e.g., "15min", "1h", "-30min")
- Support for 900+ NOAA stations nationwide

🧮 **Intelligent Processing**
- Multiple interpolation methods (cubic spline, sinusoidal)
- Dual update strategy (API + local)
- Adapts to station capabilities

## Installation

This integration is available in HACS (Home Assistant Community Store).

### Via HACS (Recommended)

1. Open HACS
2. Go to "Integrations"
3. Click "+"  and search for "NOAA Tides"
4. Click "Download"
5. Restart Home Assistant
6. Add integration via UI: Settings → Devices & Services → Add Integration

### Manual Installation

1. Copy the `custom_components/noaa_tides` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add integration via the UI

## Quick Start

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "NOAA Tides"
4. Enter your ZIP code
5. Select the nearest tide station
6. (Optional) Configure prediction intervals and chart settings

## Configuration Options

- **Prediction Intervals**: Create sensors for specific time offsets (e.g., "15min" for 15 minutes from now, "-1h" for 1 hour ago)
- **Chart Hours**: How many hours of future tide data to display (6-168 hours)
- **Chart History Hours**: How many hours of historical data to show (0-168 hours)

## Example Usage

### Automation

```yaml
automation:
  - alias: "High Tide Alert"
    trigger:
      - platform: state
        entity_id: sensor.noaa_tides_next_high_tide
    condition:
      - condition: template
        value_template: "{{ (as_timestamp(states('sensor.noaa_tides_next_high_tide')) - as_timestamp(now())) < 1800 }}"
    action:
      - service: notify.mobile_app
        data:
          title: "High Tide Soon!"
          message: "High tide in 30 minutes at {{ state_attr('sensor.noaa_tides_next_high_tide', 'height') }}m"
```

### Lovelace Card

```yaml
type: entities
entities:
  - entity: sensor.noaa_tides_current_tide_height
  - entity: sensor.noaa_tides_tide_trend
  - entity: sensor.noaa_tides_next_high_tide
  - entity: sensor.noaa_tides_next_low_tide
title: Tide Information
```

### Tide Chart Display

```yaml
type: picture-entity
entity: image.noaa_tides_tide_chart
show_name: false
show_state: false
```

## Sensors

Each station provides the following sensors:

- **Current Tide Height** (meters): Real-time or interpolated water level
- **Tide Trend** (ft/hr): Rate of change with directional icon
- **Next High Tide** (timestamp): When the next high tide occurs
- **Next Low Tide** (timestamp): When the next low tide occurs
- **Custom Prediction Sensors** (meters): Height at configured time intervals

Plus an **Image Entity** showing a beautiful SVG tide chart!

## Supported Stations

Over 900 NOAA tide stations across:
- 🇺🇸 United States coastlines
- 🏝️ Hawaiian Islands
- 🌴 Pacific territories
- 🌊 Great Lakes

## Technical Details

- Built on Home Assistant's `DataUpdateCoordinator`
- Uses NOAA CO-OPS API
- Advanced interpolation (scipy-based)
- Memory-efficient caching
- Full type hints
- Comprehensive test coverage

## Support

- 🐛 [Report bugs](https://github.com/andyleap/noaa_tides/issues)
- 💡 [Request features](https://github.com/andyleap/noaa_tides/issues)
- 📖 [Documentation](https://github.com/andyleap/noaa_tides)

## Credits

Data provided by [NOAA Center for Operational Oceanographic Products and Services](https://tidesandcurrents.noaa.gov/)
