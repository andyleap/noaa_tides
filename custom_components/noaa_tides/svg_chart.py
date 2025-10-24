"""SVG tide chart generator."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def generate_tide_chart_svg(
    predictions: list[dict[str, Any]],
    next_high: dict[str, Any] | None = None,
    next_low: dict[str, Any] | None = None,
    all_tides: list[dict[str, Any]] | None = None,
    width: int = 800,
    height: int = 400,
    local_tz: str | None = None,
) -> str:
    """Generate an SVG chart of tide predictions.

    Args:
        predictions: List of tide predictions with 'time' and 'height' keys.
                    Can be dense predictions from cubic spline interpolation for smoother curves.
        next_high: Next high tide prediction (optional, deprecated - use all_tides instead)
        next_low: Next low tide prediction (optional, deprecated - use all_tides instead)
        all_tides: List of all high/low tides with 'time', 'height', and 'type' keys.
                  Used to mark high and low tide events on the chart.
        width: Chart width in pixels (default: 800)
        height: Chart height in pixels (default: 400)
        local_tz: IANA timezone string (e.g., "America/New_York") for time display.
                 If None, displays times in UTC. (default: None)

    Returns:
        SVG markup as a string
    """
    if not predictions:
        return _generate_empty_chart(width, height, "No tide data available")

    # Chart dimensions with padding
    padding = 60
    chart_width = width - (2 * padding)
    chart_height = height - (2 * padding)

    # Convert timezone string to ZoneInfo if provided
    tz_info = None
    if local_tz:
        try:
            from zoneinfo import ZoneInfo
            tz_info = ZoneInfo(local_tz)
        except Exception:
            pass  # Fall back to UTC if timezone invalid

    # Extract data and convert meters to feet and times to local
    times = []
    for p in predictions:
        t = p["time"]
        # Convert to local timezone if possible
        if tz_info and t.tzinfo:
            t = t.astimezone(tz_info)
        times.append(t)

    heights = [p["height"] * 3.28084 for p in predictions]  # Convert m to ft

    # Calculate scales
    min_height = min(heights)
    max_height = max(heights)
    height_range = max_height - min_height

    if height_range == 0:
        height_range = 1  # Avoid division by zero

    # Generate SVG path points
    points = []
    for i, (time, tide_height) in enumerate(zip(times, heights)):
        x = padding + (i / (len(times) - 1)) * chart_width
        # Invert y because SVG y-axis goes down
        y = padding + chart_height - ((tide_height - min_height) / height_range) * chart_height
        points.append((x, y))

    # Create smooth path data using cubic Bezier curves (Catmull-Rom spline)
    path_data = f"M {points[0][0]},{points[0][1]}"

    if len(points) > 2:
        # Use cubic Bezier curves for smooth transitions
        for i in range(len(points) - 1):
            # Calculate control points for smooth curve
            p0 = points[max(0, i - 1)]
            p1 = points[i]
            p2 = points[i + 1]
            p3 = points[min(len(points) - 1, i + 2)]

            # Catmull-Rom to Bezier conversion with tension = 0.5
            tension = 0.5
            cp1_x = p1[0] + (p2[0] - p0[0]) / 6 * tension
            cp1_y = p1[1] + (p2[1] - p0[1]) / 6 * tension
            cp2_x = p2[0] - (p3[0] - p1[0]) / 6 * tension
            cp2_y = p2[1] - (p3[1] - p1[1]) / 6 * tension

            path_data += f" C {cp1_x},{cp1_y} {cp2_x},{cp2_y} {p2[0]},{p2[1]}"
    else:
        # Fallback to lines for very few points
        for x, y in points[1:]:
            path_data += f" L {x},{y}"

    # Start SVG
    # Calculate chart duration for title with smart humanization
    time_span_hours = (times[-1] - times[0]).total_seconds() / 3600

    if time_span_hours < 2:
        chart_title = "Tide Chart"
    elif time_span_hours < 48:
        # Under 48 hours: show as hours (e.g., "36-Hour Tide Chart")
        chart_title = f"{int(time_span_hours)}-Hour Tide Chart"
    else:
        # 48+ hours: show as days + hours if there are remainder hours
        days = int(time_span_hours // 24)
        remainder_hours = int(time_span_hours % 24)

        if remainder_hours == 0:
            # Exact days (e.g., "2-Day Tide Chart")
            chart_title = f"{days}-Day Tide Chart"
        elif remainder_hours <= 6:
            # Small remainder, just show days (e.g., "2-Day Tide Chart" for 50 hours)
            chart_title = f"{days}-Day Tide Chart"
        else:
            # Significant remainder, show both (e.g., "2-Day 12-Hour Tide Chart")
            chart_title = f"{days}-Day {remainder_hours}-Hour Tide Chart"

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        '  <defs>',
        '    <style>',
        '      .chart-bg { fill: #1a1a1a; }',
        '      .grid-line { stroke: #444; stroke-width: 1; }',
        '      .axis-line { stroke: #666; stroke-width: 2; }',
        '      .tide-line { stroke: #4A90E2; stroke-width: 2; fill: none; }',
        '      .tide-fill { fill: url(#tide-gradient); opacity: 0.3; }',
        '      .text { fill: #ccc; font-family: Arial, sans-serif; font-size: 12px; }',
        '      .title { fill: #fff; font-family: Arial, sans-serif; font-size: 16px; font-weight: bold; }',
        '      .high-marker { stroke: #E24A4A; stroke-width: 2; stroke-dasharray: 5,5; }',
        '      .low-marker { stroke: #4AE2A8; stroke-width: 2; stroke-dasharray: 5,5; }',
        '      .marker-text { fill: #fff; font-size: 11px; font-weight: bold; }',
        '      .date-text { fill: #fff; font-size: 12px; font-weight: bold; }',
        '    </style>',
        '    <linearGradient id="tide-gradient" x1="0%" y1="0%" x2="0%" y2="100%">',
        '      <stop offset="0%" style="stop-color:#4A90E2;stop-opacity:0.5" />',
        '      <stop offset="100%" style="stop-color:#4A90E2;stop-opacity:0.1" />',
        '    </linearGradient>',
        '  </defs>',
        '',
        f'  <rect width="{width}" height="{height}" class="chart-bg"/>',
        '',
        f'  <text x="{width/2}" y="30" text-anchor="middle" class="title">{chart_title}</text>',
        '',
    ]

    # Draw horizontal grid lines (5 lines)
    for i in range(6):
        y = padding + (i / 5) * chart_height
        grid_height = max_height - (i / 5) * height_range
        svg_parts.append(f'  <line x1="{padding}" y1="{y}" x2="{width - padding}" y2="{y}" class="grid-line"/>')
        svg_parts.append(f'  <text x="{padding - 10}" y="{y + 4}" text-anchor="end" class="text">{grid_height:.1f}</text>')

    # Draw vertical grid lines and time labels at round hour intervals
    time_span_hours = (times[-1] - times[0]).total_seconds() / 3600

    # Choose interval to get ~8 labels: try 1, 2, 3, 4, 6, or 12 hours
    target_labels = 8
    possible_intervals = [1, 2, 3, 4, 6, 12]
    interval_hours = min(possible_intervals, key=lambda h: abs(time_span_hours / h - target_labels))

    # Find the first round hour to start labeling
    from datetime import timedelta
    start_time = times[0]
    # Round up to next interval hour
    hour_offset = (interval_hours - start_time.hour % interval_hours) % interval_hours
    if hour_offset == 0 and start_time.minute > 0:
        hour_offset = interval_hours
    first_label_time = start_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=hour_offset)

    # Check if chart spans multiple days
    spans_multiple_days = (times[-1].date() != times[0].date())
    last_date_labeled = None

    # Generate labels at interval_hours apart
    current_label_time = first_label_time
    while current_label_time <= times[-1]:
        if current_label_time >= times[0]:
            # Calculate x position based on time
            time_fraction = (current_label_time - times[0]).total_seconds() / (times[-1] - times[0]).total_seconds()
            x = padding + time_fraction * chart_width
            time_label = current_label_time.strftime("%H:%M")

            svg_parts.append(f'  <line x1="{x}" y1="{padding}" x2="{x}" y2="{height - padding}" class="grid-line"/>')
            svg_parts.append(f'  <text x="{x}" y="{height - padding + 20}" text-anchor="middle" class="text">{time_label}</text>')

            # Add date label if this is a new day and chart spans multiple days
            # Only show if we've already labeled a different date (i.e., this is a transition)
            # OR if this is midnight (00:00) which marks a clear day boundary
            if spans_multiple_days:
                current_date = current_label_time.date()
                is_midnight = current_label_time.hour == 0 and current_label_time.minute == 0
                is_new_day = last_date_labeled is not None and current_date != last_date_labeled

                if is_new_day or (is_midnight and last_date_labeled is None):
                    date_label = current_label_time.strftime("%b %d")
                    svg_parts.append(f'  <text x="{x}" y="{height - padding + 35}" text-anchor="middle" class="date-text">{date_label}</text>')
                    last_date_labeled = current_date
                elif last_date_labeled is None:
                    # Track the first date without labeling it (unless it's midnight)
                    last_date_labeled = current_date

        current_label_time += timedelta(hours=interval_hours)

    # Draw axes
    svg_parts.append(f'  <line x1="{padding}" y1="{padding}" x2="{padding}" y2="{height - padding}" class="axis-line"/>')
    svg_parts.append(f'  <line x1="{padding}" y1="{height - padding}" x2="{width - padding}" y2="{height - padding}" class="axis-line"/>')

    # Create filled area under the curve
    fill_path = path_data + f" L {points[-1][0]},{height - padding} L {points[0][0]},{height - padding} Z"
    svg_parts.append(f'  <path d="{fill_path}" class="tide-fill"/>')

    # Draw the tide line
    svg_parts.append(f'  <path d="{path_data}" class="tide-line"/>')

    # Mark current time
    now = datetime.now(timezone.utc)
    if tz_info:
        now = now.astimezone(tz_info)
    if times[0] <= now <= times[-1]:
        time_fraction = (now - times[0]).total_seconds() / (times[-1] - times[0]).total_seconds()
        x = padding + time_fraction * chart_width
        svg_parts.append(f'  <line x1="{x}" y1="{padding}" x2="{x}" y2="{height - padding}" stroke="#FFA500" stroke-width="2" stroke-dasharray="3,3"/>')
        svg_parts.append(f'  <text x="{x + 5}" y="{padding + 30}" fill="#FFA500" font-size="11px" font-weight="bold">Now</text>')

    # Mark all high and low tides
    if all_tides:
        # Track text label positions to avoid overlaps
        high_label_positions = []
        low_label_positions = []

        for tide in all_tides:
            if "time" not in tide or "height" not in tide or "type" not in tide:
                continue

            tide_time = tide["time"]
            if tz_info and tide_time.tzinfo:
                tide_time = tide_time.astimezone(tz_info)

            # Only mark tides within the chart time range
            if times[0] <= tide_time <= times[-1]:
                time_fraction = (tide_time - times[0]).total_seconds() / (times[-1] - times[0]).total_seconds()
                x = padding + time_fraction * chart_width
                tide_ft = tide["height"] * 3.28084  # Convert m to ft

                if tide["type"] == "H":
                    # High tide marker
                    svg_parts.append(f'  <line x1="{x}" y1="{padding}" x2="{x}" y2="{height - padding}" class="high-marker"/>')

                    # Smart label positioning to avoid overlap
                    y_offset = 15
                    for prev_x in high_label_positions:
                        if abs(x - prev_x) < 50:  # Labels would overlap
                            y_offset += 15
                    high_label_positions.append(x)

                    svg_parts.append(f'  <text x="{x + 5}" y="{padding + y_offset}" class="marker-text">H {tide_ft:.1f}</text>')

                elif tide["type"] == "L":
                    # Low tide marker
                    svg_parts.append(f'  <line x1="{x}" y1="{padding}" x2="{x}" y2="{height - padding}" class="low-marker"/>')

                    # Smart label positioning to avoid overlap
                    y_offset = 5
                    for prev_x in low_label_positions:
                        if abs(x - prev_x) < 50:  # Labels would overlap
                            y_offset += 15
                    low_label_positions.append(x)

                    svg_parts.append(f'  <text x="{x + 5}" y="{height - padding - y_offset}" class="marker-text">L {tide_ft:.1f}</text>')

    # Fallback to next_high and next_low if all_tides not provided (backward compatibility)
    elif next_high or next_low:
        if next_high and "time" in next_high:
            high_time = next_high["time"]
            if tz_info and high_time.tzinfo:
                high_time = high_time.astimezone(tz_info)
            if times[0] <= high_time <= times[-1]:
                time_fraction = (high_time - times[0]).total_seconds() / (times[-1] - times[0]).total_seconds()
                x = padding + time_fraction * chart_width
                high_ft = next_high["height"] * 3.28084
                svg_parts.append(f'  <line x1="{x}" y1="{padding}" x2="{x}" y2="{height - padding}" class="high-marker"/>')
                svg_parts.append(f'  <text x="{x + 5}" y="{padding + 15}" class="marker-text">High {high_ft:.1f}</text>')

        if next_low and "time" in next_low:
            low_time = next_low["time"]
            if tz_info and low_time.tzinfo:
                low_time = low_time.astimezone(tz_info)
            if times[0] <= low_time <= times[-1]:
                time_fraction = (low_time - times[0]).total_seconds() / (times[-1] - times[0]).total_seconds()
                x = padding + time_fraction * chart_width
                low_ft = next_low["height"] * 3.28084
                svg_parts.append(f'  <line x1="{x}" y1="{padding}" x2="{x}" y2="{height - padding}" class="low-marker"/>')
                svg_parts.append(f'  <text x="{x + 5}" y="{height - padding - 5}" class="marker-text">Low {low_ft:.1f}</text>')

    # Add axis labels
    time_label = "Time (Local)" if tz_info else "Time (UTC)"
    svg_parts.append(f'  <text x="{width/2}" y="{height - 10}" text-anchor="middle" class="text">{time_label}</text>')
    svg_parts.append(f'  <text x="20" y="{height/2}" text-anchor="middle" transform="rotate(-90 20 {height/2})" class="text">Height (ft)</text>')

    svg_parts.append('</svg>')

    return '\n'.join(svg_parts)


def _generate_empty_chart(width: int, height: int, message: str) -> str:
    """Generate an empty chart with a message."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <rect width="{width}" height="{height}" fill="#1a1a1a"/>
  <text x="{width/2}" y="{height/2}" text-anchor="middle" fill="#ccc" font-family="Arial" font-size="16">{message}</text>
</svg>'''
