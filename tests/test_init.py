"""Test NOAA Tides component setup."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from custom_components.noaa_tides import async_setup_entry, async_unload_entry
from custom_components.noaa_tides.const import DOMAIN


async def test_setup_entry(hass: HomeAssistant) -> None:
    """Test setting up an entry."""
    entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test Station",
        data={
            "station_id": "8454000",
            "station_name": "Test Station",
            "station_capabilities": {
                "supports_hourly": True,
                "supports_observations": True,
            },
        },
        source="user",
    )

    with (
        patch(
            "custom_components.noaa_tides.coordinator.NOAATidesCoordinator.async_config_entry_first_refresh",
            return_value=None,
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=AsyncMock(return_value=True),
        ) as mock_setup,
    ):
        assert await async_setup_entry(hass, entry)
        await hass.async_block_till_done()

        # Verify platforms were set up
        assert mock_setup.called
        assert mock_setup.call_args[0][1] == [Platform.SENSOR, Platform.IMAGE]


async def test_unload_entry(hass: HomeAssistant) -> None:
    """Test unloading an entry."""
    entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="Test Station",
        data={
            "station_id": "8454000",
            "station_name": "Test Station",
            "station_capabilities": {
                "supports_hourly": True,
                "supports_observations": True,
            },
        },
        source="user",
    )

    # First set up the entry
    with (
        patch(
            "custom_components.noaa_tides.coordinator.NOAATidesCoordinator.async_config_entry_first_refresh",
            return_value=None,
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=AsyncMock(return_value=True),
        ),
    ):
        await async_setup_entry(hass, entry)
        await hass.async_block_till_done()

    # Now unload it
    with (
        patch(
            "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
            return_value=True,
        ),
        patch(
            "custom_components.noaa_tides.coordinator.NOAATidesCoordinator.async_shutdown",
            return_value=None,
        ) as mock_shutdown,
    ):
        assert await async_unload_entry(hass, entry)
        await hass.async_block_till_done()

        # Verify shutdown was called
        assert mock_shutdown.called
