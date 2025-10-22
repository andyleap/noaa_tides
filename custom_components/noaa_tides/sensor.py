"""Sensor platform for NOAA Tides integration."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
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
    """Set up NOAA Tides sensor based on a config entry."""
    coordinator: NOAATidesCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        NOAATidesCurrentHeightSensor(coordinator, entry),
        NOAATidesTrendSensor(coordinator, entry),
        NOAATidesNextHighSensor(coordinator, entry),
        NOAATidesNextLowSensor(coordinator, entry),
    ]

    async_add_entities(sensors)


class NOAATidesBaseSensor(CoordinatorEntity[NOAATidesCoordinator], SensorEntity):
    """Base class for NOAA Tides sensors."""

    def __init__(self, coordinator: NOAATidesCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.station_id)},
            name=coordinator.station_name,
            manufacturer="NOAA",
            model="Tide Station",
            configuration_url=f"https://tidesandcurrents.noaa.gov/stationhome.html?id={coordinator.station_id}",
        )


class NOAATidesCurrentHeightSensor(NOAATidesBaseSensor):
    """Sensor for current tide height."""

    _attr_name = "Current Tide Height"
    _attr_native_unit_of_measurement = UnitOfLength.METERS
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:waves"

    def __init__(self, coordinator: NOAATidesCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.station_id}_current_height"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data and "current" in self.coordinator.data:
            return self.coordinator.data["current"]["height"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "current" in self.coordinator.data:
            return {
                "last_updated": self.coordinator.data["current"]["time"].isoformat(),
            }
        return {}


class NOAATidesTrendSensor(NOAATidesBaseSensor):
    """Sensor for tide trend."""

    _attr_name = "Tide Trend"
    _attr_icon = "mdi:chart-line"

    def __init__(self, coordinator: NOAATidesCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.station_id}_trend"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if self.coordinator.data and "trend" in self.coordinator.data:
            return self.coordinator.data["trend"]
        return None

    @property
    def icon(self) -> str:
        """Return the icon based on trend."""
        if self.native_value == "rising":
            return "mdi:arrow-up"
        elif self.native_value == "falling":
            return "mdi:arrow-down"
        return "mdi:minus"


class NOAATidesNextHighSensor(NOAATidesBaseSensor):
    """Sensor for next high tide."""

    _attr_name = "Next High Tide"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:arrow-up-bold"

    def __init__(self, coordinator: NOAATidesCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.station_id}_next_high"

    @property
    def native_value(self) -> datetime | None:
        """Return the state of the sensor."""
        if (
            self.coordinator.data
            and "predictions" in self.coordinator.data
            and self.coordinator.data["predictions"]["next_high"]
        ):
            return self.coordinator.data["predictions"]["next_high"]["time"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if (
            self.coordinator.data
            and "predictions" in self.coordinator.data
            and self.coordinator.data["predictions"]["next_high"]
        ):
            return {
                "height": self.coordinator.data["predictions"]["next_high"]["height"],
                "unit": UnitOfLength.METERS,
            }
        return {}


class NOAATidesNextLowSensor(NOAATidesBaseSensor):
    """Sensor for next low tide."""

    _attr_name = "Next Low Tide"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:arrow-down-bold"

    def __init__(self, coordinator: NOAATidesCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.station_id}_next_low"

    @property
    def native_value(self) -> datetime | None:
        """Return the state of the sensor."""
        if (
            self.coordinator.data
            and "predictions" in self.coordinator.data
            and self.coordinator.data["predictions"]["next_low"]
        ):
            return self.coordinator.data["predictions"]["next_low"]["time"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if (
            self.coordinator.data
            and "predictions" in self.coordinator.data
            and self.coordinator.data["predictions"]["next_low"]
        ):
            return {
                "height": self.coordinator.data["predictions"]["next_low"]["height"],
                "unit": UnitOfLength.METERS,
            }
        return {}
