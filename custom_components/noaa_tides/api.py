"""NOAA Tides API client."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp

from .const import NOAA_API_BASE, TIDE_TYPE_HIGH, TIDE_TYPE_LOW

_LOGGER = logging.getLogger(__name__)


class NOAATidesAPI:
    """NOAA Tides API client."""

    def __init__(self, session: aiohttp.ClientSession, station_id: str) -> None:
        """Initialize the API client."""
        self.session = session
        self.station_id = station_id

    async def get_current_tide(self) -> dict[str, Any] | None:
        """Get current tide height."""
        try:
            now = datetime.now()
            params = {
                "product": "water_level",
                "application": "homeassistant",
                "begin_date": now.strftime("%Y%m%d %H:%M"),
                "end_date": (now + timedelta(minutes=1)).strftime("%Y%m%d %H:%M"),
                "datum": "MLLW",
                "station": self.station_id,
                "time_zone": "gmt",
                "units": "metric",
                "format": "json",
            }

            async with self.session.get(NOAA_API_BASE, params=params) as response:
                if response.status != 200:
                    _LOGGER.error("Error getting current tide: %s", response.status)
                    return None

                data = await response.json()
                if "data" not in data or not data["data"]:
                    _LOGGER.error("No current tide data available")
                    return None

                latest = data["data"][0]
                return {
                    "height": float(latest["v"]),
                    "time": datetime.strptime(latest["t"], "%Y-%m-%d %H:%M"),
                }

        except (aiohttp.ClientError, ValueError, KeyError) as err:
            _LOGGER.error("Error getting current tide: %s", err)
            return None

    async def get_predictions(self) -> dict[str, Any] | None:
        """Get tide predictions for next high and low tides."""
        try:
            now = datetime.now()
            params = {
                "product": "predictions",
                "application": "homeassistant",
                "begin_date": now.strftime("%Y%m%d %H:%M"),
                "end_date": (now + timedelta(days=2)).strftime("%Y%m%d %H:%M"),
                "datum": "MLLW",
                "station": self.station_id,
                "time_zone": "lst_ldt",
                "units": "metric",
                "interval": "hilo",
                "format": "json",
            }

            async with self.session.get(NOAA_API_BASE, params=params) as response:
                if response.status != 200:
                    _LOGGER.error("Error getting predictions: %s", response.status)
                    return None

                data = await response.json()
                if "predictions" not in data or not data["predictions"]:
                    _LOGGER.error("No prediction data available")
                    return None

                predictions = data["predictions"]
                next_high = None
                next_low = None

                for prediction in predictions:
                    pred_time = datetime.strptime(prediction["t"], "%Y-%m-%d %H:%M")
                    pred_type = prediction["type"]
                    pred_height = float(prediction["v"])

                    if pred_type == TIDE_TYPE_HIGH and next_high is None:
                        next_high = {
                            "time": pred_time,
                            "height": pred_height,
                        }
                    elif pred_type == TIDE_TYPE_LOW and next_low is None:
                        next_low = {
                            "time": pred_time,
                            "height": pred_height,
                        }

                    if next_high and next_low:
                        break

                return {
                    "next_high": next_high,
                    "next_low": next_low,
                }

        except (aiohttp.ClientError, ValueError, KeyError) as err:
            _LOGGER.error("Error getting predictions: %s", err)
            return None

    async def get_trend(self) -> str | None:
        """Get tide trend (rising or falling)."""
        try:
            now = datetime.now()
            past_time = now - timedelta(minutes=30)

            params = {
                "product": "water_level",
                "application": "homeassistant",
                "begin_date": past_time.strftime("%Y%m%d %H:%M"),
                "end_date": now.strftime("%Y%m%d %H:%M"),
                "datum": "MLLW",
                "station": self.station_id,
                "time_zone": "gmt",
                "units": "metric",
                "format": "json",
            }

            async with self.session.get(NOAA_API_BASE, params=params) as response:
                if response.status != 200:
                    _LOGGER.error("Error getting trend: %s", response.status)
                    return None

                data = await response.json()
                if "data" not in data or len(data["data"]) < 2:
                    _LOGGER.error("Not enough data to determine trend")
                    return None

                first_height = float(data["data"][0]["v"])
                last_height = float(data["data"][-1]["v"])

                if last_height > first_height + 0.05:
                    return "rising"
                elif last_height < first_height - 0.05:
                    return "falling"
                else:
                    return "steady"

        except (aiohttp.ClientError, ValueError, KeyError) as err:
            _LOGGER.error("Error getting trend: %s", err)
            return None

    async def get_predictions_24h(self) -> list[dict[str, Any]] | None:
        """Get detailed tide predictions for the next 24 hours for charting."""
        try:
            now = datetime.now()
            params = {
                "product": "predictions",
                "application": "homeassistant",
                "begin_date": now.strftime("%Y%m%d %H:%M"),
                "end_date": (now + timedelta(hours=24)).strftime("%Y%m%d %H:%M"),
                "datum": "MLLW",
                "station": self.station_id,
                "time_zone": "lst_ldt",
                "units": "metric",
                "interval": "h",  # Hourly predictions
                "format": "json",
            }

            async with self.session.get(NOAA_API_BASE, params=params) as response:
                if response.status != 200:
                    _LOGGER.error("Error getting 24h predictions: %s", response.status)
                    return None

                data = await response.json()
                if "predictions" not in data or not data["predictions"]:
                    _LOGGER.error("No 24h prediction data available")
                    return None

                predictions = []
                for pred in data["predictions"]:
                    pred_time = datetime.strptime(pred["t"], "%Y-%m-%d %H:%M")
                    pred_height = float(pred["v"])
                    predictions.append({
                        "time": pred_time,
                        "height": pred_height,
                        "type": pred.get("type"),  # Will be present for highs/lows
                    })

                return predictions

        except (aiohttp.ClientError, ValueError, KeyError) as err:
            _LOGGER.error("Error getting 24h predictions: %s", err)
            return None

    async def verify_station(self) -> bool:
        """Verify that the station ID is valid."""
        try:
            now = datetime.now()
            params = {
                "product": "water_level",
                "application": "homeassistant",
                "begin_date": (now - timedelta(hours=1)).strftime("%Y%m%d %H:%M"),
                "end_date": now.strftime("%Y%m%d %H:%M"),
                "datum": "MLLW",
                "station": self.station_id,
                "time_zone": "gmt",
                "units": "metric",
                "format": "json",
            }

            async with self.session.get(NOAA_API_BASE, params=params) as response:
                if response.status != 200:
                    return False

                data = await response.json()
                return "data" in data and len(data["data"]) > 0

        except (aiohttp.ClientError, ValueError, KeyError) as err:
            _LOGGER.error("Error verifying station: %s", err)
            return False
