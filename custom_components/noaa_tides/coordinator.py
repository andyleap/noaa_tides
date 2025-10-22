"""Data update coordinator for NOAA Tides."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NOAATidesAPI
from .const import CONF_STATION_ID, CONF_STATION_NAME, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class NOAATidesCoordinator(DataUpdateCoordinator):
    """NOAA Tides data update coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.station_id = entry.data[CONF_STATION_ID]
        self.station_name = entry.data[CONF_STATION_NAME]
        self.api = NOAATidesAPI(
            async_get_clientsession(hass),
            self.station_id,
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.station_id}",
            update_interval=timedelta(minutes=UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            current = await self.api.get_current_tide()
            predictions = await self.api.get_predictions()
            trend = await self.api.get_trend()
            predictions_24h = await self.api.get_predictions_24h()

            if current is None or predictions is None:
                raise UpdateFailed("Failed to fetch tide data")

            return {
                "current": current,
                "predictions": predictions,
                "trend": trend,
                "predictions_24h": predictions_24h,
            }

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
