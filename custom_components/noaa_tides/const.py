"""Constants for the NOAA Tides integration."""

DOMAIN = "noaa_tides"

CONF_STATION_ID = "station_id"
CONF_STATION_NAME = "station_name"

# API endpoints
NOAA_API_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

# Update interval
UPDATE_INTERVAL = 10  # minutes

# Tide types
TIDE_TYPE_HIGH = "H"
TIDE_TYPE_LOW = "L"
