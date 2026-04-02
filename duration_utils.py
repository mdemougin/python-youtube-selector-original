"""ISO 8601 duration parsing and human-readable formatting for YouTube video lengths."""

import re


def parse_duration(duration_str: str) -> int:
    """Parse ISO 8601 duration (e.g. PT1H2M3S) to total seconds."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds
    return 0


def format_duration(seconds: int) -> str:
    """Format seconds as H:MM:SS or M:SS."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
