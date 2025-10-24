"""Image platform for NOAA Tides integration."""
from __future__ import annotations

import logging

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NOAATidesCoordinator
from .svg_chart import generate_tide_chart_svg
from .tide_math import generate_smooth_chart_predictions

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NOAA Tides image based on a config entry."""
    coordinator: NOAATidesCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([NOAATidesChartImage(coordinator, entry)])


class NOAATidesChartImage(CoordinatorEntity[NOAATidesCoordinator], ImageEntity):
    """Image entity that displays a tide chart."""

    _attr_has_entity_name = True
    _attr_name = "Tide Chart"
    _attr_content_type = "image/svg+xml"

    def __init__(self, coordinator: NOAATidesCoordinator, entry: ConfigEntry) -> None:
        """Initialize the image entity."""
        CoordinatorEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, coordinator.hass)

        self._attr_unique_id = f"noaa_tides_{coordinator.station_id}_chart"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.station_id)},
            name=coordinator.station_name,
            manufacturer="NOAA",
            model="Tide Station",
            configuration_url=f"https://tidesandcurrents.noaa.gov/stationhome.html?id={coordinator.station_id}",
        )
        self._cached_image: bytes | None = None

    async def async_image(self) -> bytes | None:
        """Return the image."""
        try:
            # Get prediction data
            predictions = self.coordinator.get_chart_predictions()
            if not predictions:
                _LOGGER.warning("No prediction data available for chart")
                return self._cached_image

            # Generate smooth, dense predictions for better chart quality
            # Only smooth if predictions are hourly (not already dense from synthetic generation)
            # Check if predictions are approximately hourly by looking at time intervals
            if len(predictions) >= 2:
                avg_interval = (predictions[-1]["time"] - predictions[0]["time"]).total_seconds() / len(predictions)
                # If average interval > 30 minutes, apply smoothing (hourly data)
                # Otherwise predictions are already dense (synthetic at hourly intervals)
                if avg_interval > 1800:  # 30 minutes
                    smooth_predictions = generate_smooth_chart_predictions(predictions, interval_minutes=6)
                else:
                    smooth_predictions = predictions
            else:
                smooth_predictions = predictions

            # Get next high/low from coordinator data
            next_high = None
            next_low = None
            if self.coordinator.data and "predictions" in self.coordinator.data:
                coord_predictions = self.coordinator.data["predictions"]
                next_high = coord_predictions.get("next_high")
                next_low = coord_predictions.get("next_low")

            # Get all tides for marking on chart
            all_tides = None
            if self.coordinator._cached_predictions:
                all_tides = self.coordinator._cached_predictions.get("all_tides")

            # Get Home Assistant's configured timezone
            local_tz = str(self.hass.config.time_zone) if self.hass.config.time_zone else None

            # Generate SVG chart with smooth predictions
            svg_content = generate_tide_chart_svg(
                smooth_predictions,
                next_high,
                next_low,
                all_tides=all_tides,
                local_tz=local_tz,
            )

            # Convert SVG to bytes and cache it
            self._cached_image = svg_content.encode("utf-8")
            return self._cached_image

        except Exception as err:
            _LOGGER.error("Error generating tide chart: %s", err)
            return self._cached_image
