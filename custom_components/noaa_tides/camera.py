"""Camera platform for NOAA Tides integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import io
import logging
from typing import Any

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NOAATidesCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NOAA Tides camera based on a config entry."""
    coordinator: NOAATidesCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([NOAATidesChartCamera(coordinator, entry)])


class NOAATidesChartCamera(CoordinatorEntity[NOAATidesCoordinator], Camera):
    """Camera entity that displays a tide chart."""

    _attr_name = "Tide Chart"
    _attr_icon = "mdi:chart-bell-curve-cumulative"

    def __init__(self, coordinator: NOAATidesCoordinator, entry: ConfigEntry) -> None:
        """Initialize the camera."""
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)

        self._attr_unique_id = f"{coordinator.station_id}_chart"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.station_id)},
            name=coordinator.station_name,
            manufacturer="NOAA",
            model="Tide Station",
            configuration_url=f"https://tidesandcurrents.noaa.gov/stationhome.html?id={coordinator.station_id}",
        )
        self._image: bytes | None = None

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a tide chart image."""
        return await self.hass.async_add_executor_job(self._generate_chart)

    def _generate_chart(self) -> bytes | None:
        """Generate the tide chart image."""
        try:
            # Get prediction data for the next 24 hours
            predictions_data = self.coordinator.data.get("predictions_24h")
            if not predictions_data:
                _LOGGER.warning("No prediction data available for chart")
                return None

            # Create figure with dark theme
            plt.style.use('dark_background')
            fig = Figure(figsize=(10, 6), dpi=100)
            ax = fig.add_subplot(111)

            times = []
            heights = []
            high_times = []
            high_heights = []
            low_times = []
            low_heights = []

            for pred in predictions_data:
                times.append(pred["time"])
                heights.append(pred["height"])

                if pred.get("type") == "H":
                    high_times.append(pred["time"])
                    high_heights.append(pred["height"])
                elif pred.get("type") == "L":
                    low_times.append(pred["time"])
                    low_heights.append(pred["height"])

            # Plot the main tide curve
            ax.plot(times, heights, 'b-', linewidth=2, label='Tide Level')

            # Mark high and low tides
            if high_times:
                ax.scatter(high_times, high_heights, color='red', s=100,
                          zorder=5, label='High Tide', marker='^')
            if low_times:
                ax.scatter(low_times, low_heights, color='green', s=100,
                          zorder=5, label='Low Tide', marker='v')

            # Current time line
            now = datetime.now()
            ax.axvline(now, color='yellow', linestyle='--',
                      linewidth=1, alpha=0.7, label='Now')

            # Formatting
            ax.set_xlabel('Time', fontsize=12)
            ax.set_ylabel('Height (meters MLLW)', fontsize=12)
            ax.set_title(f'{self.coordinator.station_name} - 24 Hour Tide Prediction',
                        fontsize=14, fontweight='bold')

            # Format x-axis to show times nicely
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
            fig.autofmt_xdate()

            # Grid
            ax.grid(True, alpha=0.3, linestyle='--')

            # Legend
            ax.legend(loc='upper right')

            # Add current height annotation if available
            if self.coordinator.data.get("current"):
                current_height = self.coordinator.data["current"]["height"]
                ax.axhline(current_height, color='cyan', linestyle=':',
                          linewidth=1, alpha=0.5)
                ax.text(0.02, 0.98, f'Current: {current_height:.2f}m',
                       transform=ax.transAxes, fontsize=10,
                       verticalalignment='top', bbox=dict(boxstyle='round',
                       facecolor='black', alpha=0.5))

            # Save to bytes
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight',
                       facecolor='#1a1a1a', edgecolor='none')
            buf.seek(0)
            image_bytes = buf.read()
            buf.close()
            plt.close(fig)

            return image_bytes

        except Exception as err:
            _LOGGER.error("Error generating tide chart: %s", err)
            return None
