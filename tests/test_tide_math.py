"""Test tide mathematics functions."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from custom_components.noaa_tides.tide_math import (
    interpolate_tide_height,
    interpolate_from_high_low,
    estimate_trend_from_predictions,
)


def test_interpolate_tide_height_linear():
    """Test linear interpolation between two points."""
    predictions = [
        {"time": datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), "height": 1.0},
        {"time": datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc), "height": 2.0},
    ]

    target_time = datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc)
    result = interpolate_tide_height(predictions, target_time)

    assert result is not None
    assert abs(result["height"] - 1.5) < 0.01  # Should be halfway


def test_interpolate_from_high_low():
    """Test sinusoidal interpolation between high and low tide."""
    high_tide = {"time": datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), "height": 2.0}
    low_tide = {"time": datetime(2024, 1, 1, 18, 0, tzinfo=timezone.utc), "height": 0.0}

    # Midpoint should be around mean height
    target_time = datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc)
    result = interpolate_from_high_low(high_tide, low_tide, target_time)

    assert result is not None
    assert 0.5 < result["height"] < 1.5  # Should be near mean (1.0)


def test_estimate_trend_rising():
    """Test trend estimation for rising tide."""
    predictions = [
        {"time": datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), "height": 1.0},
        {"time": datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc), "height": 1.5},
        {"time": datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc), "height": 2.0},
    ]

    trend = estimate_trend_from_predictions(predictions, datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc))
    assert trend == "rising"


def test_estimate_trend_falling():
    """Test trend estimation for falling tide."""
    predictions = [
        {"time": datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), "height": 2.0},
        {"time": datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc), "height": 1.5},
        {"time": datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc), "height": 1.0},
    ]

    trend = estimate_trend_from_predictions(predictions, datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc))
    assert trend == "falling"


def test_estimate_trend_steady():
    """Test trend estimation for steady tide."""
    predictions = [
        {"time": datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc), "height": 1.5},
        {"time": datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc), "height": 1.5},
        {"time": datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc), "height": 1.5},
    ]

    trend = estimate_trend_from_predictions(predictions, datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc))
    assert trend == "steady"
