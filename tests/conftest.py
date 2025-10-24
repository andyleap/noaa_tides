"""Fixtures for NOAA Tides tests."""
from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""
    yield


@pytest.fixture
def mock_noaa_api():
    """Mock NOAA API responses."""
    with patch("custom_components.noaa_tides.api.NOAATidesAPI") as mock_api:
        yield mock_api
