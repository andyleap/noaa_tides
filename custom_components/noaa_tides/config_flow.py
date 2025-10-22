"""Config flow for NOAA Tides integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NOAATidesAPI
from .const import CONF_STATION_ID, CONF_STATION_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STATION_ID): str,
        vol.Required(CONF_STATION_NAME): str,
    }
)


async def validate_station(hass: HomeAssistant, station_id: str) -> bool:
    """Validate the station ID."""
    session = async_get_clientsession(hass)
    api = NOAATidesAPI(session, station_id)
    return await api.verify_station()


class NOAATidesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NOAA Tides."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            station_id = user_input[CONF_STATION_ID]

            # Check if station is already configured
            await self.async_set_unique_id(station_id)
            self._abort_if_unique_id_configured()

            # Validate station ID
            if not await validate_station(self.hass, station_id):
                errors["base"] = "invalid_station"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_STATION_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
