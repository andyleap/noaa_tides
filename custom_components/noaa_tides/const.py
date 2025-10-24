"""Constants for the NOAA Tides integration."""

DOMAIN = "noaa_tides"

CONF_STATION_ID = "station_id"
CONF_STATION_NAME = "station_name"
CONF_PREDICTION_INTERVALS = "prediction_intervals"
CONF_STATION_CAPABILITIES = "station_capabilities"
CONF_CHART_HOURS = "chart_hours"
CONF_CHART_HISTORY_HOURS = "chart_history_hours"

# Default prediction intervals (empty - no additional predictions)
DEFAULT_PREDICTION_INTERVALS = []
DEFAULT_CHART_HOURS = 24  # 24 hours for chart display
DEFAULT_CHART_HISTORY_HOURS = 0  # No historical data by default

# API endpoints
NOAA_API_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

# Update interval
UPDATE_INTERVAL = 10  # minutes

# Tide types
TIDE_TYPE_HIGH = "H"
TIDE_TYPE_LOW = "L"

# Tide mathematics constants
TIDE_SEMI_PERIOD_HOURS = 6.2  # Average time between high and low tide (~12.4h / 2)
TREND_STEADY_THRESHOLD_METERS = 0.1  # Height change threshold for "steady" trend
RATE_DERIVATIVE_DELTA_SECONDS = 300.0  # Time delta for numerical derivative (5 minutes)
