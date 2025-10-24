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

    # Add dynamic sensors for each configured prediction interval
    intervals = coordinator.get_prediction_intervals()
    for interval_minutes in intervals:
        sensors.append(NOAATidesPredictionSensor(coordinator, entry, interval_minutes))

    async_add_entities(sensors)


class NOAATidesBaseSensor(CoordinatorEntity[NOAATidesCoordinator], SensorEntity):
    """Base class for NOAA Tides sensors."""

    _attr_has_entity_name = True

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
        self._attr_unique_id = f"noaa_tides_{coordinator.station_id}_current_height"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data and "current" in self.coordinator.data:
            current = self.coordinator.data["current"]
            if current is not None:
                return current["height"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "current" in self.coordinator.data:
            current = self.coordinator.data["current"]
            if current is not None:
                return {
                    "last_updated": current["time"].isoformat(),
                }
        return {}


class NOAATidesTrendSensor(NOAATidesBaseSensor):
    """Sensor for tide trend rate."""

    _attr_name = "Tide Trend"
    _attr_native_unit_of_measurement = "ft/hr"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:chart-line"

    def __init__(self, coordinator: NOAATidesCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"noaa_tides_{coordinator.station_id}_trend"

    @property
    def native_value(self) -> float | None:
        """Return the rate of change in ft/hr."""
        if self.coordinator.data and "tide_rate" in self.coordinator.data:
            rate_m_per_hr = self.coordinator.data["tide_rate"]
            if rate_m_per_hr is not None:
                # Convert meters/hour to feet/hour
                return round(rate_m_per_hr * 3.28084, 2)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        rate = self.native_value
        if rate is not None:
            if rate > 0.1:
                direction = "rising"
            elif rate < -0.1:
                direction = "falling"
            else:
                direction = "steady"
            return {"direction": direction}
        return {}

    @property
    def icon(self) -> str:
        """Return the icon based on trend."""
        rate = self.native_value
        if rate is not None:
            if rate > 0.1:
                return "mdi:arrow-up"
            elif rate < -0.1:
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
        self._attr_unique_id = f"noaa_tides_{coordinator.station_id}_next_high"

    @property
    def native_value(self) -> datetime | None:
        """Return the state of the sensor."""
        if self.coordinator.data and "predictions" in self.coordinator.data:
            predictions = self.coordinator.data["predictions"]
            if predictions and predictions.get("next_high"):
                return predictions["next_high"]["time"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "predictions" in self.coordinator.data:
            predictions = self.coordinator.data["predictions"]
            if predictions and predictions.get("next_high"):
                return {
                    "height": predictions["next_high"]["height"],
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
        self._attr_unique_id = f"noaa_tides_{coordinator.station_id}_next_low"

    @property
    def native_value(self) -> datetime | None:
        """Return the state of the sensor."""
        if self.coordinator.data and "predictions" in self.coordinator.data:
            predictions = self.coordinator.data["predictions"]
            if predictions and predictions.get("next_low"):
                return predictions["next_low"]["time"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.coordinator.data and "predictions" in self.coordinator.data:
            predictions = self.coordinator.data["predictions"]
            if predictions and predictions.get("next_low"):
                return {
                    "height": predictions["next_low"]["height"],
                    "unit": UnitOfLength.METERS,
                }
        return {}


class NOAATidesPredictionSensor(NOAATidesBaseSensor):
    """Sensor for tide height prediction at a specific interval."""

    _attr_native_unit_of_measurement = UnitOfLength.METERS
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: NOAATidesCoordinator,
        entry: ConfigEntry,
        interval_minutes: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self.interval_minutes = interval_minutes

        # Create a friendly name and ID based on the interval
        if interval_minutes < 0:
            # Historical prediction
            abs_minutes = abs(interval_minutes)
            if abs_minutes < 60:
                time_str = f"{abs_minutes}min ago"
                id_str = f"{abs_minutes}m_ago"
            elif abs_minutes < 1440:
                hours = abs_minutes / 60
                time_str = f"{hours:.1f}h ago" if hours != int(hours) else f"{int(hours)}h ago"
                id_str = f"{int(abs_minutes)}m_ago"
            else:
                days = abs_minutes / 1440
                time_str = f"{days:.1f}d ago" if days != int(days) else f"{int(days)}d ago"
                id_str = f"{int(abs_minutes)}m_ago"
        else:
            # Future prediction
            if interval_minutes < 60:
                time_str = f"{interval_minutes}min"
                id_str = f"{interval_minutes}m"
            elif interval_minutes < 1440:
                hours = interval_minutes / 60
                time_str = f"{hours:.1f}h" if hours != int(hours) else f"{int(hours)}h"
                id_str = f"{interval_minutes}m"
            else:
                days = interval_minutes / 1440
                time_str = f"{days:.1f}d" if days != int(days) else f"{int(days)}d"
                id_str = f"{interval_minutes}m"

        self._attr_name = f"Tide Height ({time_str})"
        self._attr_unique_id = f"noaa_tides_{coordinator.station_id}_prediction_{id_str}"
        self._attr_icon = "mdi:wave" if interval_minutes < 0 else "mdi:waves-arrow-right"

    @property
    def native_value(self) -> float | None:
        """Return the predicted tide height."""
        predictions = self.coordinator.calculate_interval_predictions()
        if self.interval_minutes in predictions:
            return predictions[self.interval_minutes]["height"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        predictions = self.coordinator.calculate_interval_predictions()
        if self.interval_minutes in predictions:
            pred = predictions[self.interval_minutes]
            return {
                "prediction_time": pred["time"].isoformat(),
                "interval_minutes": self.interval_minutes,
            }
        return {}
