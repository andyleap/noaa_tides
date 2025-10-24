# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-XX

### Added
- Initial release of NOAA Tides integration
- Real-time tide height monitoring from NOAA stations
- Support for stations across the United States
- Automatic station discovery by ZIP code
- Current tide height sensor with MLLW datum
- Tide trend sensor with rate in ft/hr
- Next high and low tide timestamp sensors
- Dynamic prediction sensors at custom intervals (historical and future)
- SVG tide chart image entity with configurable time ranges
- Support for both observation-capable and prediction-only stations
- Intelligent interpolation (cubic spline for hourly data, sinusoidal for high/low)
- Chart smoothing with 6-minute interval predictions
- Timezone-aware chart display (uses Home Assistant's configured timezone)
- HACS compatible installation

### Features
- **Dual update strategy**: API updates every 10 minutes, local interpolation every minute
- **Flexible chart configuration**: 6-168 hours of future and historical data
- **Custom prediction intervals**: Configure sensors for any time offset (e.g., "15min", "1h", "-30min")
- **Station capability detection**: Automatically adapts to station features
- **Multiple interpolation methods**: Linear for hourly data, sinusoidal for tidal curves
- **Memory efficient**: Proper resource cleanup on integration unload

### Technical
- Uses NOAA CO-OPS API for tide data
- Requires scipy for advanced interpolation
- Built on Home Assistant's DataUpdateCoordinator pattern
- Follows Home Assistant integration best practices
- Full type hints and comprehensive logging
- Tested with Python 3.11 and 3.12

## [Unreleased]

### Changed
### Fixed
### Added
### Removed
