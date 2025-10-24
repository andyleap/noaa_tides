# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration that provides real-time tide information from NOAA (National Oceanic and Atmospheric Administration) tide stations. The integration is HACS-compatible and implements the device integration pattern with sensors and image entities.

## Architecture

### Core Components

**Platform Integration (`__init__.py`)**
- Implements standard Home Assistant entry setup/teardown
- Registers platforms: `Platform.SENSOR` and `Platform.IMAGE`
- Creates and stores the coordinator in `hass.data[DOMAIN][entry.entry_id]`

**Data Coordinator (`coordinator.py`)**
- `NOAATidesCoordinator`: Central data management using Home Assistant's `DataUpdateCoordinator`
- **Dual update strategy**:
  - API updates every 10 minutes (configurable via `UPDATE_INTERVAL`)
  - Local updates every 1 minute (interpolates between API data)
- Caches prediction data in `_cached_predictions` for efficient local updates
- Provides methods: `get_chart_predictions()`, `calculate_interval_predictions()`

**API Client (`api.py`)**
- `NOAATidesAPI`: Handles all NOAA API communication
- Key endpoint: `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter`
- Station capability detection: `detect_capabilities()` checks if station supports hourly predictions and water level observations
- Optimized data fetching: `get_all_predictions()` fetches multiple data types in parallel
- ZIP code search: `search_stations_by_zip()` uses zippopotam.us API for geocoding

**Configuration Flow (`config_flow.py`)**
- **Two-step setup**:
  1. User enters ZIP code
  2. Displays nearest stations with distance and capabilities
- Options flow allows configuring:
  - Custom prediction intervals (e.g., "15min", "1h", "-30min" for historical)
  - Chart display hours (6-168 hours)
  - Chart history hours (0-168 hours)
- Duration parsing supports: minutes, hours, days with various suffixes

**Tide Mathematics (`tide_math.py`)**
- **Two interpolation methods**:
  - `interpolate_tide_height()`: Linear interpolation for hourly data (more accurate)
  - `interpolate_from_high_low()`: Sinusoidal interpolation between consecutive tides
- `calculate_tide_rate()`: Derivative of sinusoidal function for instantaneous rate
- `generate_synthetic_predictions()`: Creates hourly data from high/low tides for prediction-only stations

**Sensor Platform (`sensor.py`)**
- Base sensors: Current Height, Trend (rate in ft/hr), Next High, Next Low
- Dynamic sensors: Created for each configured prediction interval
- Trend sensor shows rate with directional icon (arrows/minus)

**Image Platform (`image.py`)**
- Generates SVG tide charts via `svg_chart.py` (not analyzed but referenced)
- Updates with coordinator data
- Caches generated images

### Data Flow

1. **Initial Load**: Coordinator fetches predictions, observations, high/low tides from NOAA API
2. **Capability Detection**: During config flow, API checks what data types station supports
3. **Data Processing**:
   - Stations with observations use actual current data
   - Prediction-only stations use interpolated data (hourly linear or high/low sinusoidal)
4. **Local Updates**: Every minute, coordinator recalculates interpolated values without API calls
5. **Chart Generation**: On-demand generation from cached predictions (synthetic if needed)

### Station Capabilities

Not all NOAA stations support the same data types:
- **Hourly predictions**: Some stations only provide high/low tides
- **Water level observations**: Some stations only provide predictions
- Capabilities stored in `CONF_STATION_CAPABILITIES` during setup
- Affects which interpolation method is used and whether observations are fetched

## Development Commands

### Testing the Integration

Test in a Home Assistant development environment:
```bash
# Copy integration to custom_components
cp -r custom_components/noaa_tides /path/to/homeassistant/custom_components/

# Restart Home Assistant
# Then add integration via UI: Settings → Devices & Services → Add Integration
```

### Testing API Calls

Manually test NOAA API endpoints:
```bash
# Get current water level (not all stations support this)
curl "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=water_level&station=8454000&begin_date=20250101%2012:00&end_date=20250101%2013:00&datum=MLLW&time_zone=gmt&units=metric&format=json&application=homeassistant"

# Get tide predictions (high/low)
curl "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=predictions&station=8454000&begin_date=20250101&end_date=20250102&datum=MLLW&time_zone=gmt&units=metric&interval=hilo&format=json&application=homeassistant"

# Get hourly predictions (not all stations support this)
curl "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=predictions&station=8454000&begin_date=20250101&end_date=20250102&datum=MLLW&time_zone=gmt&units=metric&interval=h&format=json&application=homeassistant"
```

Example station IDs:
- `8454000` - Providence, RI
- `8518750` - The Battery, NY
- `9414290` - San Francisco, CA

## Important Implementation Details

### Timezone Handling
- All NOAA API calls use GMT (`time_zone=gmt`)
- All internal datetime objects use `timezone.utc`
- Conversion to local time handled by Home Assistant's timestamp device class

### Datum
- All measurements use MLLW (Mean Lower Low Water) datum
- Consistent across all API calls for accurate comparisons

### Interpolation Strategy
The coordinator intelligently selects interpolation method:
1. Try actual current observations first (most accurate)
2. Fall back to hourly predictions with linear interpolation
3. Fall back to high/low tides with sinusoidal interpolation

### Update Intervals
- **API updates**: Every 10 minutes (respects NOAA rate limits)
- **Local updates**: Every 1 minute (no API calls, uses cached data)
- Chart hours and prediction intervals affect how much data is fetched from API

### Error Handling
- Graceful degradation: If current data unavailable, use interpolation
- If trend unavailable from observations, estimate from predictions
- Capability detection prevents unnecessary API calls to unsupported endpoints

## Configuration

### Config Entry Data
- `CONF_STATION_ID`: 7-digit NOAA station ID
- `CONF_STATION_NAME`: Friendly name for the station
- `CONF_STATION_CAPABILITIES`: Dict with `supports_hourly` and `supports_observations`

### Options
- `CONF_PREDICTION_INTERVALS`: List of integers (minutes, can be negative for historical)
- `CONF_CHART_HOURS`: Integer (6-168), hours of future data for chart
- `CONF_CHART_HISTORY_HOURS`: Integer (0-168), hours of historical data for chart

## Common Modification Patterns

### Adding a New Sensor Type
1. Create sensor class in [sensor.py](custom_components/noaa_tides/sensor.py) extending `NOAATidesBaseSensor`
2. Implement `native_value` property using `self.coordinator.data`
3. Add to sensor list in `async_setup_entry()`

### Modifying Interpolation
- Linear interpolation logic: [tide_math.py:9-79](custom_components/noaa_tides/tide_math.py#L9-L79)
- Sinusoidal interpolation logic: [tide_math.py:82-178](custom_components/noaa_tides/tide_math.py#L82-L178)
- Rate calculation uses derivative of sine function: [tide_math.py:250-325](custom_components/noaa_tides/tide_math.py#L250-L325)

### Adding API Endpoints
- All API calls go through `NOAATidesAPI` in [api.py](custom_components/noaa_tides/api.py)
- Use `NOAA_API_BASE` constant from [const.py](custom_components/noaa_tides/const.py)
- Follow existing patterns for error handling and JSON parsing

### Adjusting Update Frequency
- Change `UPDATE_INTERVAL` in [const.py:21](custom_components/noaa_tides/const.py#L21) for API updates
- Local update interval set in [coordinator.py:69-73](custom_components/noaa_tides/coordinator.py#L69-L73)

## Station Discovery

The integration uses NOAA's metadata API to search stations:
- Geocodes ZIP codes via zippopotam.us (free, no API key)
- Fetches stations from `https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.xml`
- Calculates haversine distance to find nearest stations
- Filters by `type=tidepredictions` for stations with tide data
- Shows which stations have live water level data vs predictions-only
