"""Config flow for NOAA Tides integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode

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
)

_LOGGER = logging.getLogger(__name__)


def parse_duration_to_minutes(duration_str: str) -> int | None:
    """Parse a duration string to minutes.

    Supports formats like:
    - "15" or "15min" or "15m" -> 15 minutes (future)
    - "-15min" or "-15m" -> -15 minutes (past/historical)
    - "1h" or "1hr" or "1hour" -> 60 minutes
    - "-1h" -> -60 minutes (1 hour ago)
    - "1.5h" -> 90 minutes
    - "30s" or "30sec" -> 0.5 minutes
    """
    duration_str = duration_str.strip().lower()

    # Try to parse as timedelta using HA's parser
    try:
        # Parse using Home Assistant's duration parser
        # Formats: "HH:MM:SS", "HH:MM", seconds as int/float, or with unit suffixes
        import re

        # Check for common patterns (including negative values for historical)
        # Pattern: optional negative sign, number, followed by optional unit
        match = re.match(r'^(-?[\d.]+)\s*([a-z]*)$', duration_str)
        if not match:
            return None

        value_str, unit = match.groups()
        try:
            value = float(value_str)
        except ValueError:
            return None

        # Convert to minutes based on unit
        minutes = None
        if not unit or unit in ('m', 'min', 'mins', 'minute', 'minutes'):
            minutes = value
        elif unit in ('h', 'hr', 'hrs', 'hour', 'hours'):
            minutes = value * 60
        elif unit in ('s', 'sec', 'secs', 'second', 'seconds'):
            minutes = value / 60
        elif unit in ('d', 'day', 'days'):
            minutes = value * 1440
        else:
            return None

        # For positive values, require at least 1 minute
        # For negative values, allow any amount
        if minutes is not None:
            return int(minutes)

        return None

    except Exception:
        return None


async def validate_station(hass: HomeAssistant, station_id: str) -> bool:
    """Validate the station ID."""
    session = async_get_clientsession(hass)
    api = NOAATidesAPI(session, station_id)
    return await api.verify_station()


class NOAATidesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NOAA Tides."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._stations: list[dict[str, Any]] = []
        self._zip_code: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - ask for zip code."""
        errors: dict[str, str] = {}

        if user_input is not None:
            zip_code = user_input["zip_code"]
            self._zip_code = zip_code

            # Try to find stations near this zip
            session = async_get_clientsession(self.hass)
            self._stations = await NOAATidesAPI.search_stations_by_zip(session, zip_code)

            if not self._stations:
                errors["base"] = "no_stations"
            else:
                # Show station selection
                return await self.async_step_select_station()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("zip_code"): str,
            }),
            errors=errors,
        )

    async def async_step_select_station(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle station selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # User selected a station
            station_id = user_input["station"]

            # Check if station is already configured
            await self.async_set_unique_id(station_id)
            self._abort_if_unique_id_configured()

            # Find the station details
            station_name = None
            for station in self._stations:
                if station["id"] == station_id:
                    distance = station["distance"]
                    state_str = f", {station['state']}" if station['state'] else ""
                    station_name = f"{station['name']}{state_str}"
                    break

            if not station_name:
                # Fallback if we can't find it
                station_name = f"Station {station_id}"

            # Validate station ID and detect capabilities
            if not await validate_station(self.hass, station_id):
                errors["base"] = "invalid_station"
            else:
                # Detect station capabilities
                session = async_get_clientsession(self.hass)
                api = NOAATidesAPI(session, station_id)
                capabilities = await api.detect_capabilities()

                return self.async_create_entry(
                    title=station_name,
                    data={
                        CONF_STATION_ID: station_id,
                        CONF_STATION_NAME: station_name,
                        CONF_STATION_CAPABILITIES: capabilities,
                    },
                )

        # Create options for selector with distance info
        options = []
        for s in self._stations:
            state_str = f", {s['state']}" if s['state'] else ""
            pred_only = " [Predictions Only]" if not s.get('has_waterlevel', False) else ""
            label = f"{s['name']}{state_str} - {s['distance']:.1f} mi{pred_only} ({s['id']})"
            options.append({"label": label, "value": s['id']})

        return self.async_show_form(
            step_id="select_station",
            data_schema=vol.Schema({
                vol.Required("station"): SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> NOAATidesOptionsFlow:
        """Get the options flow for this handler."""
        return NOAATidesOptionsFlow(config_entry)


class NOAATidesOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for NOAA Tides."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Parse the comma-separated intervals
            intervals_str = user_input.get("prediction_intervals", "")
            intervals = []

            if intervals_str.strip():
                # Parse comma-separated duration values
                interval_parts = [x.strip() for x in intervals_str.split(",") if x.strip()]

                for part in interval_parts:
                    minutes = parse_duration_to_minutes(part)
                    if minutes is None or minutes == 0:
                        return self.async_show_form(
                            step_id="init",
                            data_schema=self._get_options_schema(),
                            errors={"prediction_intervals": "invalid_intervals"},
                        )
                    intervals.append(minutes)

            # Parse chart hours
            chart_hours = user_input.get("chart_hours", DEFAULT_CHART_HOURS)
            try:
                chart_hours = int(chart_hours)
                if chart_hours < 6 or chart_hours > 168:  # 6 hours to 7 days
                    return self.async_show_form(
                        step_id="init",
                        data_schema=self._get_options_schema(),
                        errors={"chart_hours": "invalid_chart_hours"},
                    )
            except ValueError:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._get_options_schema(),
                    errors={"chart_hours": "invalid_chart_hours"},
                )

            # Parse chart history hours
            chart_history_hours = user_input.get("chart_history_hours", DEFAULT_CHART_HISTORY_HOURS)
            try:
                chart_history_hours = int(chart_history_hours)
                if chart_history_hours < 0 or chart_history_hours > 168:  # 0 to 7 days
                    return self.async_show_form(
                        step_id="init",
                        data_schema=self._get_options_schema(),
                        errors={"chart_history_hours": "invalid_chart_history_hours"},
                    )
            except ValueError:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._get_options_schema(),
                    errors={"chart_history_hours": "invalid_chart_history_hours"},
                )

            return self.async_create_entry(
                title="",
                data={
                    CONF_PREDICTION_INTERVALS: intervals,
                    CONF_CHART_HOURS: chart_hours,
                    CONF_CHART_HISTORY_HOURS: chart_history_hours,
                },
            )

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_options_schema(),
        )

    def _get_options_schema(self) -> vol.Schema:
        """Get the options schema."""
        # Get current intervals or use defaults
        current_intervals = self.config_entry.options.get(
            CONF_PREDICTION_INTERVALS,
            DEFAULT_PREDICTION_INTERVALS,
        )

        # Get current chart hours or use default
        current_chart_hours = self.config_entry.options.get(
            CONF_CHART_HOURS,
            DEFAULT_CHART_HOURS,
        )

        # Get current chart history hours or use default
        current_chart_history_hours = self.config_entry.options.get(
            CONF_CHART_HISTORY_HOURS,
            DEFAULT_CHART_HISTORY_HOURS,
        )

        # Convert list to comma-separated string
        intervals_str = ", ".join(str(i) for i in current_intervals)

        return vol.Schema({
            vol.Optional(
                "prediction_intervals",
                default=intervals_str,
            ): str,
            vol.Optional(
                "chart_hours",
                default=current_chart_hours,
            ): int,
            vol.Optional(
                "chart_history_hours",
                default=current_chart_history_hours,
            ): int,
        })
