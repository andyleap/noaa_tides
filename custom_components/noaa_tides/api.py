"""NOAA Tides API client."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import math
from typing import Any
import xml.etree.ElementTree as ET

import aiohttp

from .const import NOAA_API_BASE, TIDE_TYPE_HIGH, TIDE_TYPE_LOW

_LOGGER = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in miles using haversine formula."""
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    # Earth radius in miles
    radius = 3956

    return c * radius


class NOAATidesAPI:
    """NOAA Tides API client."""

    def __init__(self, session: aiohttp.ClientSession, station_id: str | None = None) -> None:
        """Initialize the API client."""
        self.session = session
        self.station_id = station_id

    @staticmethod
    async def geocode_zip(session: aiohttp.ClientSession, zip_code: str) -> tuple[float, float] | None:
        """Get lat/lon for a US zip code using free API."""
        try:
            # Use zippopotam.us - free, no API key required
            url = f"http://api.zippopotam.us/us/{zip_code}"

            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    _LOGGER.error("Error geocoding zip %s: %s", zip_code, response.status)
                    return None

                data = await response.json()

                if "places" in data and len(data["places"]) > 0:
                    lat = float(data["places"][0]["latitude"])
                    lon = float(data["places"][0]["longitude"])
                    _LOGGER.info("Geocoded zip %s to lat=%f, lon=%f", zip_code, lat, lon)
                    return (lat, lon)

                return None

        except Exception as err:
            _LOGGER.error("Error geocoding zip code: %s", err)
            return None

    @staticmethod
    async def search_stations_by_zip(session: aiohttp.ClientSession, zip_code: str) -> list[dict[str, Any]]:
        """Search for tide stations near a zip code."""
        try:
            # Geocode the zip code
            coords = await NOAATidesAPI.geocode_zip(session, zip_code)
            if not coords:
                _LOGGER.error("Could not geocode zip code: %s", zip_code)
                return []

            user_lat, user_lon = coords

            # First, get all water level stations (stations with live data)
            waterlevel_ids = set()
            try:
                wl_response = await session.get(
                    "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.xml",
                    params={"type": "waterlevels", "units": "metric"}
                )
                if wl_response.status == 200:
                    wl_xml = await wl_response.text()
                    wl_root = ET.fromstring(wl_xml)
                    for wl_station in wl_root.findall(".//Station"):
                        wl_id_elem = wl_station.find("id")
                        if wl_id_elem is not None and wl_id_elem.text:
                            waterlevel_ids.add(wl_id_elem.text)
                    _LOGGER.info("Found %d water level stations", len(waterlevel_ids))
            except Exception as err:
                _LOGGER.warning("Could not fetch water level stations: %s", err)

            # Fetch all tide prediction stations
            url = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.xml"
            params = {
                "type": "tidepredictions",  # All stations with tide predictions
                "units": "metric",
            }

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    _LOGGER.error("Error fetching station list: %s", response.status)
                    return []

                xml_data = await response.text()
                root = ET.fromstring(xml_data)

                stations = []
                for station in root.findall(".//Station"):
                    # XML elements, not attributes
                    id_elem = station.find("id")
                    name_elem = station.find("name")
                    state_elem = station.find("state")
                    lat_elem = station.find("lat")
                    lon_elem = station.find("lng")

                    if (id_elem is not None and name_elem is not None and
                        lat_elem is not None and lon_elem is not None):
                        try:
                            station_id = id_elem.text
                            name = name_elem.text
                            state = state_elem.text if state_elem is not None and state_elem.text else ""
                            lat = float(lat_elem.text)
                            lon = float(lon_elem.text)

                            # Calculate distance
                            distance = haversine_distance(user_lat, user_lon, lat, lon)

                            # Check if station has live water level data
                            has_waterlevel = station_id in waterlevel_ids

                            stations.append({
                                "id": station_id,
                                "name": name,
                                "state": state,
                                "lat": lat,
                                "lon": lon,
                                "distance": distance,
                                "has_waterlevel": has_waterlevel,
                            })
                        except (ValueError, AttributeError, TypeError) as err:
                            continue

                # Sort by distance and return top 10
                stations.sort(key=lambda x: x["distance"])
                nearest = stations[:10]

                _LOGGER.info("Found %d nearest stations to zip %s", len(nearest), zip_code)
                return nearest

        except Exception as err:
            _LOGGER.error("Error searching stations: %s", err)
            return []


    async def get_all_predictions(
        self,
        hours_before: int = 0,
        hours_after: int = 24,
        supports_hourly: bool = True,
        supports_observations: bool = True,
    ) -> dict[str, Any] | None:
        """Get all predictions data in a single call (high/low tides and hourly).

        Args:
            hours_before: Number of hours of historical observations to fetch (default: 0)
            hours_after: Number of hours of future predictions to fetch (default: 24)
            supports_hourly: Whether station supports hourly predictions (default: True)
            supports_observations: Whether station supports observations (default: True)
        """
        try:
            now = datetime.now(timezone.utc)

            # Fetch future hourly predictions only if supported
            params_hourly = None
            if supports_hourly:
                params_hourly = {
                    "product": "predictions",
                    "application": "homeassistant",
                    "begin_date": now.strftime("%Y%m%d %H:%M"),
                    "end_date": (now + timedelta(hours=hours_after)).strftime("%Y%m%d %H:%M"),
                    "datum": "MLLW",
                    "station": self.station_id,
                    "time_zone": "gmt",
                    "units": "metric",
                    "interval": "h",  # Hourly data
                    "format": "json",
                }

            # Fetch historical water level observations if requested and supported
            params_historical = None
            if hours_before > 0 and supports_observations:
                params_historical = {
                    "product": "water_level",
                    "application": "homeassistant",
                    "begin_date": (now - timedelta(hours=hours_before)).strftime("%Y%m%d %H:%M"),
                    "end_date": now.strftime("%Y%m%d %H:%M"),
                    "datum": "MLLW",
                    "station": self.station_id,
                    "time_zone": "gmt",
                    "units": "metric",
                    "format": "json",
                }

            # Fetch high/low predictions - broader range for interpolation
            # Need to fetch enough historical data to cover the requested history_hours
            # Add 12 hour buffer to ensure we have bracketing tides
            hilo_hours_before = max(12, hours_before + 12)
            params_hilo = {
                "product": "predictions",
                "application": "homeassistant",
                "begin_date": (now - timedelta(hours=hilo_hours_before)).strftime("%Y%m%d %H:%M"),
                "end_date": (now + timedelta(hours=hours_after)).strftime("%Y%m%d %H:%M"),
                "datum": "MLLW",
                "station": self.station_id,
                "time_zone": "gmt",
                "units": "metric",
                "interval": "hilo",
                "format": "json",
            }

            # Fetch all data with proper context managers
            async with self.session.get(NOAA_API_BASE, params=params_hilo) as hilo_response:
                hilo_data = await hilo_response.json() if hilo_response.status == 200 else None

            hourly_data = None
            if params_hourly:
                async with self.session.get(NOAA_API_BASE, params=params_hourly) as hourly_response:
                    hourly_data = await hourly_response.json() if hourly_response.status == 200 else None

            historical_data_raw = None
            if params_historical:
                async with self.session.get(NOAA_API_BASE, params=params_historical) as historical_response:
                    historical_data_raw = await historical_response.json() if historical_response.status == 200 else None

            try:
                # Process hourly data (future predictions)
                hourly_predictions = None
                if hourly_data and "predictions" in hourly_data and hourly_data["predictions"]:
                    hourly_predictions = []
                    for pred in hourly_data["predictions"]:
                        pred_time = datetime.strptime(pred["t"], "%Y-%m-%d %H:%M")
                        pred_time = pred_time.replace(tzinfo=timezone.utc)
                        pred_height = float(pred["v"])
                        hourly_predictions.append({
                            "time": pred_time,
                            "height": pred_height,
                        })
                    _LOGGER.debug("Station %s: Processed %d hourly predictions", self.station_id, len(hourly_predictions))
                elif params_hourly:
                    _LOGGER.warning("Station %s: Hourly predictions requested but unavailable", self.station_id)

                # Process high/low data - store ALL tides
                all_tides = []
                current_time = datetime.now(timezone.utc)

                if hilo_data and "predictions" in hilo_data and hilo_data["predictions"]:
                        for prediction in hilo_data["predictions"]:
                            pred_time = datetime.strptime(prediction["t"], "%Y-%m-%d %H:%M")
                            pred_time = pred_time.replace(tzinfo=timezone.utc)
                            pred_type = prediction["type"]
                            pred_height = float(prediction["v"])

                            tide_data = {
                                "time": pred_time,
                                "height": pred_height,
                                "type": pred_type,
                            }
                            all_tides.append(tide_data)

                # Find the two consecutive tides that bracket the current time
                # These are used for interpolation
                prev_tide = None
                next_tide = None
                for tide in all_tides:
                    if tide["time"] <= current_time:
                        prev_tide = tide
                    elif tide["time"] > current_time and next_tide is None:
                        next_tide = tide
                        break

                # For backward compatibility, also find next_high and next_low
                # (for the sensors that display next high/low times)
                next_high = None
                next_low = None
                for tide in all_tides:
                    if tide["time"] > current_time:
                        if tide["type"] == TIDE_TYPE_HIGH and next_high is None:
                            next_high = {
                                "time": tide["time"],
                                "height": tide["height"],
                            }
                        elif tide["type"] == TIDE_TYPE_LOW and next_low is None:
                            next_low = {
                                "time": tide["time"],
                                "height": tide["height"],
                            }
                    if next_high and next_low:
                        break

                # Process historical water level observations
                historical_data = []
                if historical_data_raw and "data" in historical_data_raw and historical_data_raw["data"]:
                    for obs in historical_data_raw["data"]:
                            obs_time = datetime.strptime(obs["t"], "%Y-%m-%d %H:%M")
                            obs_time = obs_time.replace(tzinfo=timezone.utc)
                            obs_height = float(obs["v"])
                            historical_data.append({
                                "time": obs_time,
                                "height": obs_height,
                            })
                    _LOGGER.debug("Station %s: Fetched %d historical observations",
                                 self.station_id, len(historical_data))
                elif params_historical:
                    _LOGGER.debug("Station %s: Historical data requested but unavailable", self.station_id)

                # Merge historical and future predictions into a single timeline
                # Both are already time-ordered, so concatenation preserves order
                combined_predictions = historical_data + (hourly_predictions if hourly_predictions else [])

                if next_high is None and next_low is None:
                    _LOGGER.error("No prediction data available")
                    return None

                return {
                    "next_high": next_high,
                    "next_low": next_low,
                    "prev_tide": prev_tide,  # Previous tide (for interpolation)
                    "next_tide": next_tide,  # Next tide (for interpolation)
                    "all_tides": all_tides,  # All high/low tides for chart generation
                    "hourly_predictions": combined_predictions,  # Combined historical + future hourly data
                    "historical_data": historical_data,  # Separate historical data
                }
            except Exception as e:
                _LOGGER.error("Error processing prediction data: %s", e)
                raise

        except (aiohttp.ClientError, ValueError, KeyError) as err:
            _LOGGER.error("Error getting predictions: %s", err)
            return None

    async def verify_station(self) -> bool:
        """Verify that the station ID is valid by checking for predictions."""
        try:
            now = datetime.now()
            params = {
                "product": "predictions",
                "application": "homeassistant",
                "begin_date": now.strftime("%Y%m%d %H:%M"),
                "end_date": (now + timedelta(days=1)).strftime("%Y%m%d %H:%M"),
                "datum": "MLLW",
                "station": self.station_id,
                "time_zone": "lst_ldt",
                "units": "metric",
                "interval": "hilo",
                "format": "json",
            }

            async with self.session.get(NOAA_API_BASE, params=params) as response:
                if response.status != 200:
                    return False

                data = await response.json()
                # Check for predictions (works for all tide stations)
                return "predictions" in data and len(data["predictions"]) > 0

        except (aiohttp.ClientError, ValueError, KeyError) as err:
            _LOGGER.error("Error verifying station: %s", err)
            return False

    async def detect_capabilities(self) -> dict[str, bool]:
        """Detect what data types this station supports.

        Returns:
            Dict with keys: supports_hourly, supports_observations
        """
        capabilities = {
            "supports_hourly": False,
            "supports_observations": False,
        }

        now = datetime.now(timezone.utc)

        # Test hourly predictions
        try:
            params_hourly = {
                "product": "predictions",
                "application": "homeassistant",
                "begin_date": now.strftime("%Y%m%d %H:%M"),
                "end_date": (now + timedelta(hours=6)).strftime("%Y%m%d %H:%M"),
                "datum": "MLLW",
                "station": self.station_id,
                "time_zone": "gmt",
                "units": "metric",
                "interval": "h",
                "format": "json",
            }

            async with self.session.get(NOAA_API_BASE, params=params_hourly, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if "predictions" in data and data["predictions"]:
                        capabilities["supports_hourly"] = True
                        _LOGGER.info("Station %s supports hourly predictions", self.station_id)
        except Exception as err:
            _LOGGER.debug("Station %s does not support hourly predictions: %s", self.station_id, err)

        # Test water level observations
        try:
            params_obs = {
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

            async with self.session.get(NOAA_API_BASE, params=params_obs, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if "data" in data and data["data"]:
                        capabilities["supports_observations"] = True
                        _LOGGER.info("Station %s supports water level observations", self.station_id)
        except Exception as err:
            _LOGGER.debug("Station %s does not support observations: %s", self.station_id, err)

        return capabilities
