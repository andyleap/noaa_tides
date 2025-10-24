"""Mathematical utilities for tide calculations."""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Any

from .const import TIDE_SEMI_PERIOD_HOURS, TREND_STEADY_THRESHOLD_METERS, RATE_DERIVATIVE_DELTA_SECONDS

_LOGGER = logging.getLogger(__name__)


def interpolate_tide_height(
    hourly_predictions: list[dict[str, Any]],
    target_time: datetime | None = None,
) -> dict[str, Any] | None:
    """
    Interpolate tide height from hourly predictions.

    Uses cubic spline interpolation for better accuracy when possible,
    falls back to linear interpolation for fewer data points.

    Args:
        hourly_predictions: List of hourly tide predictions or observations
        target_time: Time to interpolate for (defaults to now)

    Returns:
        Dictionary with 'height' and 'time' keys, or None if unable to interpolate
    """
    if not hourly_predictions or len(hourly_predictions) < 2:
        return None

    if target_time is None:
        target_time = datetime.now(timezone.utc)

    # Ensure target_time is timezone-aware
    if target_time.tzinfo is None:
        target_time = target_time.replace(tzinfo=timezone.utc)

    # If we have enough points, try cubic interpolation
    if len(hourly_predictions) >= 4:
        try:
            from scipy.interpolate import interp1d

            # Extract times and heights
            times = [p["time"] for p in hourly_predictions]
            heights = [p["height"] for p in hourly_predictions]

            # Check if target_time is within range
            if not (times[0] <= target_time <= times[-1]):
                # Outside range, use edge values
                if target_time < times[0]:
                    return {"height": heights[0], "time": target_time}
                else:
                    return {"height": heights[-1], "time": target_time}

            # Convert times to seconds since first prediction
            start_time = times[0]
            time_seconds = [(t - start_time).total_seconds() for t in times]
            target_seconds = (target_time - start_time).total_seconds()

            # Remove duplicates (keep first occurrence)
            seen_times = set()
            unique_times = []
            unique_heights = []
            for t, h in zip(time_seconds, heights):
                if t not in seen_times:
                    seen_times.add(t)
                    unique_times.append(t)
                    unique_heights.append(h)

            # Need at least 4 unique points for cubic
            if len(unique_times) < 4:
                raise ValueError(f"Only {len(unique_times)} unique points after deduplication")

            # Use piecewise cubic interpolation (more stable than global spline)
            interp_func = interp1d(unique_times, unique_heights, kind='cubic', bounds_error=False, fill_value=(unique_heights[0], unique_heights[-1]))

            # Interpolate at target time
            interpolated_height = float(interp_func(target_seconds))

            return {
                "height": interpolated_height,
                "time": target_time,
            }

        except ImportError:
            _LOGGER.debug("scipy not available, using linear interpolation")
        except Exception as err:
            _LOGGER.debug("Error in cubic interpolation: %s, falling back to linear", err)

    # Fall back to linear interpolation
    # Find the two predictions that bracket the target time
    before = None
    after = None

    for i, pred in enumerate(hourly_predictions):
        pred_time = pred["time"]

        if pred_time <= target_time:
            before = pred
        elif pred_time > target_time and after is None:
            after = pred
            break

    # If we can't bracket the time, use the closest point
    if before is None:
        # Target time is before all predictions
        return {
            "height": hourly_predictions[0]["height"],
            "time": target_time,
        }

    if after is None:
        # Target time is after all predictions
        return {
            "height": hourly_predictions[-1]["height"],
            "time": target_time,
        }

    # Linear interpolation between hourly data points
    time_span = (after["time"] - before["time"]).total_seconds()
    time_offset = (target_time - before["time"]).total_seconds()

    if time_span == 0:
        ratio = 0
    else:
        ratio = time_offset / time_span

    # Simple linear interpolation
    interpolated_height = before["height"] + (after["height"] - before["height"]) * ratio

    return {
        "height": interpolated_height,
        "time": target_time,
    }


def interpolate_from_high_low(
    next_high: dict[str, Any] | None,
    next_low: dict[str, Any] | None,
    target_time: datetime | None = None,
) -> dict[str, Any] | None:
    """
    Interpolate tide height from high/low tide predictions.

    Uses sinusoidal interpolation between high and low tides.
    This is more accurate than linear interpolation for prediction-only stations.

    Args:
        next_high: Next high tide with 'time' and 'height' keys
        next_low: Next low tide with 'time' and 'height' keys
        target_time: Time to interpolate for (defaults to now)

    Returns:
        Dictionary with 'height' and 'time' keys, or None if unable to interpolate
    """
    if not next_high or not next_low:
        return None

    if target_time is None:
        target_time = datetime.now(timezone.utc)

    # Ensure target_time is timezone-aware
    if target_time.tzinfo is None:
        target_time = target_time.replace(tzinfo=timezone.utc)

    high_time = next_high["time"]
    low_time = next_low["time"]
    high_height = next_high["height"]
    low_height = next_low["height"]

    # Determine which comes first and setup the tide cycle
    if high_time < low_time:
        # High tide comes first, then low
        first_time = high_time
        first_height = high_height
        second_time = low_time
        second_height = low_height
    else:
        # Low tide comes first, then high
        first_time = low_time
        first_height = low_height
        second_time = high_time
        second_height = high_height

    # If target time is before first tide, need to estimate backwards
    if target_time < first_time:
        # Estimate the previous opposite tide using semi-period
        # Average tidal period is ~12.4 hours between same tides
        # So opposite tide is ~6.2 hours before
        time_before_first = timedelta(hours=TIDE_SEMI_PERIOD_HOURS)
        prev_time = first_time - time_before_first
        prev_height = second_height  # Opposite type

        # Now interpolate between previous and first
        period = (first_time - prev_time).total_seconds()
        elapsed = (target_time - prev_time).total_seconds()
    elif target_time > second_time:
        # Estimate the next tide after second using semi-period
        time_after_second = timedelta(hours=TIDE_SEMI_PERIOD_HOURS)
        next_time = second_time + time_after_second
        next_height = first_height  # Opposite type

        # Now interpolate between second and next
        period = (next_time - second_time).total_seconds()
        elapsed = (target_time - second_time).total_seconds()
        first_time = second_time
        first_height = second_height
        second_height = next_height
    else:
        # Target time is between the two tides (normal case)
        period = (second_time - first_time).total_seconds()
        elapsed = (target_time - first_time).total_seconds()

    if period == 0:
        return {"height": first_height, "time": target_time}

    # Sinusoidal interpolation (tides follow sine wave pattern)
    # Height varies as: first_height + amplitude * cos(phase)
    # where phase goes from 0 to π over the period
    amplitude = (second_height - first_height) / 2
    mean_height = (first_height + second_height) / 2

    # Phase goes from 0 to π
    phase = (elapsed / period) * math.pi

    # Use cosine: starts at first height, goes to second height
    interpolated_height = mean_height - amplitude * math.cos(phase)

    return {
        "height": interpolated_height,
        "time": target_time,
    }


def generate_synthetic_predictions(
    all_tides: list[dict[str, Any]],
    hours: int = 24,
    history_hours: int = 0,
) -> list[dict[str, Any]] | None:
    """
    Generate synthetic hourly predictions from all high/low tides.

    Uses piecewise sinusoidal interpolation between consecutive tides.

    Args:
        all_tides: List of all high/low tide predictions with 'time', 'height', and 'type' keys
        hours: Number of hours to generate into the future (default 24)
        history_hours: Number of hours to generate into the past (default 0)

    Returns:
        List of predictions with 'time' and 'height' keys, or None
    """
    if not all_tides or len(all_tides) < 2:
        return None

    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=history_hours)
    end_time = now + timedelta(hours=hours)
    predictions = []

    # Generate hourly predictions from past to future
    # Need to include the final hour, so use range(total_hours + 1)
    total_hours = history_hours + hours
    for hour_offset in range(total_hours + 1):
        target_time = start_time + timedelta(hours=hour_offset)

        # Find the two tides that bracket this time
        prev_tide = None
        next_tide = None

        for i, tide in enumerate(all_tides):
            if tide["time"] <= target_time:
                prev_tide = tide
            if tide["time"] > target_time and next_tide is None:
                next_tide = tide
                break

        # If we have both bracketing tides, interpolate
        if prev_tide and next_tide:
            period = (next_tide["time"] - prev_tide["time"]).total_seconds()
            elapsed = (target_time - prev_tide["time"]).total_seconds()

            if period > 0:
                # Sinusoidal interpolation between the two tides
                amplitude = (next_tide["height"] - prev_tide["height"]) / 2
                mean_height = (prev_tide["height"] + next_tide["height"]) / 2
                phase = (elapsed / period) * math.pi
                height = mean_height - amplitude * math.cos(phase)

                predictions.append({
                    "time": target_time,
                    "height": height,
                })
        elif prev_tide and not next_tide:
            # Past the last known tide, use the last height
            predictions.append({
                "time": target_time,
                "height": prev_tide["height"],
            })
        elif next_tide and not prev_tide:
            # Before the first known tide, use the first height
            predictions.append({
                "time": target_time,
                "height": next_tide["height"],
            })

    return predictions if predictions else None


def calculate_tide_rate(
    predictions: list[dict[str, Any]] | None = None,
    next_high: dict[str, Any] | None = None,
    next_low: dict[str, Any] | None = None,
    target_time: datetime | None = None,
) -> float | None:
    """
    Calculate the rate of tide change in meters per hour.

    Uses the derivative of cubic spline interpolation when predictions are available
    for higher accuracy, otherwise falls back to sinusoidal derivative.
    Positive values = rising, negative = falling.

    Args:
        predictions: List of tide predictions (hourly data preferred)
        next_high: Next high tide with 'time' and 'height' keys (fallback)
        next_low: Next low tide with 'time' and 'height' keys (fallback)
        target_time: Time to calculate rate for (defaults to now)

    Returns:
        Rate in meters/hour, or None if unable to calculate
    """
    if target_time is None:
        target_time = datetime.now(timezone.utc)

    # Ensure target_time is timezone-aware
    if target_time.tzinfo is None:
        target_time = target_time.replace(tzinfo=timezone.utc)

    # Try numerical derivative using cubic interpolation (most accurate)
    if predictions and len(predictions) >= 4:
        try:
            from scipy.interpolate import interp1d

            # Extract times and heights
            times = [p["time"] for p in predictions]
            heights = [p["height"] for p in predictions]

            # Check if target_time is within range
            if times[0] <= target_time <= times[-1]:
                # Convert times to seconds since first prediction
                start_time = times[0]
                time_seconds = [(t - start_time).total_seconds() for t in times]
                target_seconds = (target_time - start_time).total_seconds()

                # Remove duplicates (keep first occurrence)
                seen_times = set()
                unique_times = []
                unique_heights = []
                for t, h in zip(time_seconds, heights):
                    if t not in seen_times:
                        seen_times.add(t)
                        unique_times.append(t)
                        unique_heights.append(h)

                # Need at least 4 unique points for cubic
                if len(unique_times) < 4:
                    raise ValueError(f"Only {len(unique_times)} unique points after deduplication")

                # Use piecewise cubic interpolation
                interp_func = interp1d(unique_times, unique_heights, kind='cubic', bounds_error=False, fill_value=(unique_heights[0], unique_heights[-1]))

                # Calculate numerical derivative using small time delta
                delta_t = RATE_DERIVATIVE_DELTA_SECONDS
                h1 = float(interp_func(target_seconds - delta_t / 2))
                h2 = float(interp_func(target_seconds + delta_t / 2))

                # Rate in meters per second
                rate_per_second = (h2 - h1) / delta_t

                # Convert to meters per hour
                rate_per_hour = rate_per_second * 3600

                _LOGGER.debug("Calculated tide rate using cubic interpolation: %.3f m/hr", rate_per_hour)
                return rate_per_hour

        except ImportError:
            _LOGGER.debug("scipy not available for rate calculation, using sinusoidal")
        except Exception as err:
            _LOGGER.debug("Error in cubic interpolation rate calculation: %s, falling back", err)

    # Fall back to sinusoidal derivative using high/low tides
    if not next_high or not next_low:
        return None

    high_time = next_high["time"]
    low_time = next_low["time"]
    high_height = next_high["height"]
    low_height = next_low["height"]

    # Determine which comes first
    if high_time < low_time:
        first_time = high_time
        first_height = high_height
        second_time = low_time
        second_height = low_height
    else:
        first_time = low_time
        first_height = low_height
        second_time = high_time
        second_height = high_height

    # Handle times outside the known tides
    if target_time < first_time:
        time_before_first = timedelta(hours=TIDE_SEMI_PERIOD_HOURS)
        prev_time = first_time - time_before_first
        period = (first_time - prev_time).total_seconds()
        elapsed = (target_time - prev_time).total_seconds()
        amplitude = (first_height - second_height) / 2
    elif target_time > second_time:
        time_after_second = timedelta(hours=TIDE_SEMI_PERIOD_HOURS)
        next_time = second_time + time_after_second
        period = (next_time - second_time).total_seconds()
        elapsed = (target_time - second_time).total_seconds()
        amplitude = (first_height - second_height) / 2
    else:
        period = (second_time - first_time).total_seconds()
        elapsed = (target_time - first_time).total_seconds()
        amplitude = (second_height - first_height) / 2

    if period == 0:
        return 0.0

    # Derivative of sinusoidal function: amplitude * (π/period) * sin(π*t/period)
    phase = (elapsed / period) * math.pi
    rate_per_second = amplitude * (math.pi / period) * math.sin(phase)

    # Convert to meters per hour
    rate_per_hour = rate_per_second * 3600

    return rate_per_hour


def estimate_trend_from_predictions(
    hourly_predictions: list[dict[str, Any]],
    target_time: datetime | None = None,
) -> str | None:
    """
    Estimate tide trend (rising/falling/steady) from predictions.

    Args:
        hourly_predictions: List of hourly tide predictions
        target_time: Time to check trend for (defaults to now)

    Returns:
        "rising", "falling", "steady", or None
    """
    if not hourly_predictions or len(hourly_predictions) < 3:
        return None

    if target_time is None:
        target_time = datetime.now(timezone.utc)

    # Ensure target_time is timezone-aware
    if target_time.tzinfo is None:
        target_time = target_time.replace(tzinfo=timezone.utc)

    # Find predictions around target time
    closest_idx = 0
    min_diff = float('inf')

    for i, pred in enumerate(hourly_predictions):
        diff = abs((pred["time"] - target_time).total_seconds())
        if diff < min_diff:
            min_diff = diff
            closest_idx = i

    # Get surrounding predictions to determine trend
    if closest_idx == 0:
        # At the beginning, look forward
        height_before = hourly_predictions[0]["height"]
        height_after = hourly_predictions[1]["height"]
    elif closest_idx == len(hourly_predictions) - 1:
        # At the end, look backward
        height_before = hourly_predictions[-2]["height"]
        height_after = hourly_predictions[-1]["height"]
    else:
        # In the middle, average the trend
        height_before = hourly_predictions[closest_idx - 1]["height"]
        height_after = hourly_predictions[closest_idx + 1]["height"]

    height_diff = height_after - height_before

    # Threshold for "steady" trend
    if abs(height_diff) < TREND_STEADY_THRESHOLD_METERS:
        return "steady"
    elif height_diff > 0:
        return "rising"
    else:
        return "falling"


def generate_smooth_chart_predictions(
    predictions: list[dict[str, Any]],
    interval_minutes: int = 6,
) -> list[dict[str, Any]]:
    """
    Generate smooth, dense predictions using local cubic interpolation.

    This creates a much smoother chart by:
    1. Using local cubic interpolation (4-point windows) instead of linear
    2. Generating points every 6 minutes (or configurable interval)
    3. Avoiding wild oscillations at boundaries by using local splines

    Args:
        predictions: List of prediction points with 'time' and 'height' keys
        interval_minutes: Minutes between generated points (default 6)

    Returns:
        List of dense predictions for smooth charting
    """
    if not predictions or len(predictions) < 4:
        # Need at least 4 points for cubic interpolation, fall back to original
        return predictions

    try:
        from scipy.interpolate import interp1d
        import numpy as np

        # Extract times and heights
        times = [p["time"] for p in predictions]
        heights = [p["height"] for p in predictions]

        # Convert times to seconds since first prediction
        start_time = times[0]
        time_seconds = [(t - start_time).total_seconds() for t in times]

        # Remove duplicates (keep first occurrence)
        seen_times = set()
        unique_times = []
        unique_heights = []
        for t, h in zip(time_seconds, heights):
            if t not in seen_times:
                seen_times.add(t)
                unique_times.append(t)
                unique_heights.append(h)

        if len(unique_times) < 4:
            _LOGGER.warning("Not enough unique points after deduplication (%d), falling back", len(unique_times))
            return predictions

        time_seconds_array = np.array(unique_times)
        heights_array = np.array(unique_heights)

        # Use cubic interpolation with not-a-knot boundary conditions
        # This prevents oscillations at the edges while maintaining smoothness
        interp_func = interp1d(
            time_seconds_array,
            heights_array,
            kind='cubic',
            bounds_error=False,
            fill_value=(heights_array[0], heights_array[-1])  # Use edge values outside range
        )

        # Generate dense time points
        total_duration = time_seconds_array[-1]
        num_points = int(total_duration / (interval_minutes * 60)) + 1
        dense_time_seconds = np.linspace(0, total_duration, num_points)

        # Interpolate heights at dense time points
        dense_heights = interp_func(dense_time_seconds)

        # Convert back to datetime objects
        dense_predictions = []
        for t_sec, height in zip(dense_time_seconds, dense_heights):
            time = start_time + timedelta(seconds=float(t_sec))
            dense_predictions.append({
                "time": time,
                "height": float(height),
            })

        _LOGGER.debug(
            "Generated %d smooth predictions from %d original points using cubic interpolation",
            len(dense_predictions), len(predictions)
        )

        return dense_predictions

    except ImportError:
        _LOGGER.warning("scipy not available, falling back to original predictions")
        return predictions
    except Exception as err:
        _LOGGER.error("Error generating smooth predictions: %s, falling back to original", err)
        return predictions
