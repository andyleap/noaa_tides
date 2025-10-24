"""Data update coordinator for NOAA Tides."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NOAATidesAPI
from .const import (
    CONF_CHART_HISTORY_HOURS,
    CONF_CHART_HOURS,
    CONF_PREDICTION_INTERVALS,
    CONF_STATION_CAPABILITIES,
    CONF_STATION_ID,
    CONF_STATION_NAME,
    DEFAULT_CHART_HISTORY_HOURS,
    DEFAULT_CHART_HOURS,
    DEFAULT_PREDICTION_INTERVALS,
    DOMAIN,
    UPDATE_INTERVAL,
)
from .tide_math import (
    calculate_tide_rate,
    estimate_trend_from_predictions,
    generate_synthetic_predictions,
    interpolate_from_high_low,
    interpolate_tide_height,
)

_LOGGER = logging.getLogger(__name__)


class NOAATidesCoordinator(DataUpdateCoordinator):
    """NOAA Tides data update coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.station_id = entry.data[CONF_STATION_ID]
        self.station_name = entry.data[CONF_STATION_NAME]
        self.entry = entry
        self.api = NOAATidesAPI(
            async_get_clientsession(hass),
            self.station_id,
        )
        # Get station capabilities, defaulting to supporting everything for older configs
        self.capabilities = entry.data.get(CONF_STATION_CAPABILITIES, {
            "supports_hourly": True,
            "supports_observations": True,
        })
        self.last_update_time: datetime | None = None
        self._cached_predictions = None  # Cache API data
        self._local_update_unsub = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.station_id}",
            update_interval=timedelta(minutes=UPDATE_INTERVAL),
        )

        # Set up frequent local updates every minute
        self._local_update_unsub = async_track_time_interval(
            hass,
            self._async_local_update,
            timedelta(minutes=1),
        )

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and clean up resources."""
        if self._local_update_unsub:
            self._local_update_unsub()
            self._local_update_unsub = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            # Calculate how many hours of predictions we need based on configured intervals
            intervals = self.get_prediction_intervals()
            max_future_minutes = max((i for i in intervals if i > 0), default=0)
            min_past_minutes = min((i for i in intervals if i < 0), default=0)

            # Get configured chart hours (for historical data)
            chart_hours = self.entry.options.get(CONF_CHART_HOURS, DEFAULT_CHART_HOURS)
            chart_history_hours = self.entry.options.get(CONF_CHART_HISTORY_HOURS, DEFAULT_CHART_HISTORY_HOURS)

            # Calculate hours needed: 12 hours buffer + max of requirements
            # - Historical: max of chart history hours or prediction interval requirements
            # - Future: max of chart hours or prediction interval requirements
            hours_before = 12 + max(
                chart_history_hours,
                int(abs(min_past_minutes) / 60) if min_past_minutes < 0 else 0,
            )
            hours_after = 12 + max(
                chart_hours,
                int(max_future_minutes / 60),
            )

            # Get all predictions data in optimized single call
            all_predictions = await self.api.get_all_predictions(
                hours_before=hours_before,
                hours_after=hours_after,
                supports_hourly=self.capabilities.get("supports_hourly", True),
                supports_observations=self.capabilities.get("supports_observations", True),
            )

            # At minimum we need predictions
            if all_predictions is None:
                raise UpdateFailed("Failed to fetch tide predictions")

            # Separate actual hourly data from what we'll use for charting
            hourly_predictions = all_predictions.get("hourly_predictions")  # Actual hourly data (or combined with historical)
            next_high = all_predictions.get("next_high")
            next_low = all_predictions.get("next_low")
            prev_tide = all_predictions.get("prev_tide")
            next_tide = all_predictions.get("next_tide")
            all_tides = all_predictions.get("all_tides", [])

            _LOGGER.info(
                "Station %s: Got predictions - hourly data: %s points, next_high: %s, next_low: %s, bracketing tides: %s",
                self.station_id,
                len(hourly_predictions) if hourly_predictions else 0,
                next_high is not None,
                next_low is not None,
                (prev_tide is not None and next_tide is not None),
            )

            # Interpolate current data from predictions
            # Try hourly predictions first if available (linear interpolation)
            current = None
            if hourly_predictions:
                current = interpolate_tide_height(hourly_predictions)
                if current:
                    _LOGGER.debug(
                        "Interpolated current height from hourly: %.2f meters at %s",
                        current["height"],
                        current["time"],
                    )

            # Fall back to bracketing tide interpolation (sinusoidal between consecutive tides)
            if current is None and prev_tide and next_tide:
                current = interpolate_from_high_low(prev_tide, next_tide)
                if current:
                    _LOGGER.info(
                        "Interpolated current height from bracketing tides (%s at %s to %s at %s): %.2f meters",
                        prev_tide["type"], prev_tide["time"].strftime("%H:%M"),
                        next_tide["type"], next_tide["time"].strftime("%H:%M"),
                        current["height"],
                    )

            # Calculate tide rate (meters/hour)
            # Pass hourly predictions for more accurate cubic spline derivative
            tide_rate = None
            if hourly_predictions or (next_high and next_low):
                tide_rate = calculate_tide_rate(
                    predictions=hourly_predictions,
                    next_high=next_high,
                    next_low=next_low,
                )
                if tide_rate is not None:
                    _LOGGER.debug("Calculated tide rate: %.3f m/hr", tide_rate)

            # Estimate trend from hourly predictions
            trend = None
            if hourly_predictions:
                trend = estimate_trend_from_predictions(hourly_predictions)
                if trend:
                    _LOGGER.debug("Estimated trend from predictions: %s", trend)

            # Cache the prediction data for local updates and charting
            self._cached_predictions = {
                "next_high": next_high,
                "next_low": next_low,
                "all_tides": all_tides,
                "hourly_predictions": hourly_predictions,  # Actual hourly data (for interpolation)
                "hours_after": hours_after,  # Store how many hours we fetched for synthetic generation
            }

            # Update the timestamp
            self.last_update_time = datetime.now(timezone.utc)

            return {
                "current": current,  # May be interpolated for prediction-only stations
                "predictions": {
                    "next_high": next_high,
                    "next_low": next_low,
                },
                "trend": trend,  # May be estimated from predictions
                "tide_rate": tide_rate,  # Rate in meters/hour
                # Note: chart_predictions generated on-demand in image.py
            }

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _async_local_update(self, now: datetime | None = None) -> None:
        """Update interpolated values without fetching from API."""
        if not self._cached_predictions:
            return  # No cached data yet

        try:
            next_high = self._cached_predictions.get("next_high")
            next_low = self._cached_predictions.get("next_low")
            hourly_predictions = self._cached_predictions.get("hourly_predictions")
            all_tides = self._cached_predictions.get("all_tides", [])

            # Recalculate interpolated current height
            # Use actual hourly data if available (linear), otherwise bracketing tides (sinusoidal)
            current = None
            if hourly_predictions:
                current = interpolate_tide_height(hourly_predictions)

            # Fall back to bracketing tide interpolation
            if current is None and all_tides:
                current_time = datetime.now(timezone.utc)
                prev_tide = None
                next_tide = None
                for tide in all_tides:
                    if tide["time"] <= current_time:
                        prev_tide = tide
                    elif tide["time"] > current_time and next_tide is None:
                        next_tide = tide
                        break

                if prev_tide and next_tide:
                    current = interpolate_from_high_low(prev_tide, next_tide)

            # Recalculate tide rate with improved accuracy
            tide_rate = None
            if hourly_predictions or (next_high and next_low):
                tide_rate = calculate_tide_rate(
                    predictions=hourly_predictions,
                    next_high=next_high,
                    next_low=next_low,
                )

            # Recalculate trend from actual hourly predictions only (not synthetic)
            trend = None
            if hourly_predictions:
                trend = estimate_trend_from_predictions(hourly_predictions)

            # Update the timestamp
            self.last_update_time = datetime.now(timezone.utc)

            # Update coordinator data without triggering API fetch
            self.async_set_updated_data({
                "current": current,
                "predictions": {
                    "next_high": next_high,
                    "next_low": next_low,
                },
                "trend": trend,
                "tide_rate": tide_rate,
            })

            _LOGGER.debug("Local update completed for station %s", self.station_id)

        except Exception as err:
            _LOGGER.error("Error during local update: %s", err)

    def get_prediction_intervals(self) -> list[int]:
        """Get the configured prediction intervals."""
        return self.entry.options.get(
            CONF_PREDICTION_INTERVALS,
            DEFAULT_PREDICTION_INTERVALS,
        )

    def get_chart_predictions(self) -> list[dict[str, Any]] | None:
        """Get predictions for charting (generates synthetic if needed)."""
        if not self._cached_predictions:
            return None

        # Get configured chart hours
        chart_hours = self.entry.options.get(CONF_CHART_HOURS, DEFAULT_CHART_HOURS)
        chart_history_hours = self.entry.options.get(CONF_CHART_HISTORY_HOURS, DEFAULT_CHART_HISTORY_HOURS)

        hourly_predictions = self._cached_predictions.get("hourly_predictions")

        # If we have hourly data, filter it to the requested chart range
        if hourly_predictions:
            now = datetime.now(timezone.utc)
            start_time = now - timedelta(hours=chart_history_hours)
            end_time = now + timedelta(hours=chart_hours)

            # Filter predictions to requested time range with small buffer
            # Use slightly wider range (30 minute buffer) to ensure we capture boundary points
            buffer = timedelta(minutes=30)
            filtered_predictions = [
                p for p in hourly_predictions
                if (start_time - buffer) <= p["time"] <= (end_time + buffer)
            ]

            if filtered_predictions:
                _LOGGER.debug("Filtered %d hourly predictions to %d for chart (%dh history + %dh future)",
                             len(hourly_predictions), len(filtered_predictions),
                             chart_history_hours, chart_hours)
                return filtered_predictions

            # If filtering resulted in no data, return all (edge case)
            return hourly_predictions

        # Otherwise, generate synthetic predictions from high/low tides for chart display
        all_tides = self._cached_predictions.get("all_tides")

        if all_tides:
            # Generate synthetic from history to future
            synthetic = generate_synthetic_predictions(
                all_tides,
                hours=chart_hours,
                history_hours=chart_history_hours
            )
            if synthetic:
                _LOGGER.debug("Generated %d synthetic chart predictions (%dh history + %dh future) from %d tides",
                             len(synthetic), chart_history_hours, chart_hours, len(all_tides))
            return synthetic

        return None

    def calculate_interval_predictions(self) -> dict[int, dict[str, Any]]:
        """Calculate tide predictions at configured intervals (future or historical)."""
        intervals = self.get_prediction_intervals()
        predictions = {}

        if not self._cached_predictions:
            return predictions

        hourly_predictions = self._cached_predictions.get("hourly_predictions")
        all_tides = self._cached_predictions.get("all_tides", [])

        now = datetime.now(timezone.utc)

        for interval_minutes in intervals:
            target_time = now + timedelta(minutes=interval_minutes)

            # Try to interpolate from hourly predictions first (includes historical if available)
            # Uses linear interpolation for accuracy
            predicted_height = None
            if hourly_predictions:
                result = interpolate_tide_height(hourly_predictions, target_time)
                if result:
                    predicted_height = result["height"]

            # Fall back to bracketing tide interpolation
            # Find the two consecutive tides that bracket the target time
            if predicted_height is None and all_tides:
                prev_tide = None
                next_tide = None
                for tide in all_tides:
                    if tide["time"] <= target_time:
                        prev_tide = tide
                    elif tide["time"] > target_time and next_tide is None:
                        next_tide = tide
                        break

                # Interpolate between the bracketing tides
                if prev_tide and next_tide:
                    result = interpolate_from_high_low(prev_tide, next_tide, target_time)
                    if result:
                        predicted_height = result["height"]

            if predicted_height is not None:
                predictions[interval_minutes] = {
                    "time": target_time,
                    "height": predicted_height,
                }

        return predictions
