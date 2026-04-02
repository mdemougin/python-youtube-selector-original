"""Tests for duration_utils."""

import pytest

from duration_utils import format_duration, parse_duration


@pytest.mark.parametrize(
    ("iso_str", "expected_seconds"),
    [
        ("PT1H2M3S", 3600 + 120 + 3),
        ("PT45M", 45 * 60),
        ("PT30S", 30),
        ("PT1H", 3600),
        ("PT0S", 0),
        ("PT", 0),
        ("not-a-duration", 0),
    ],
)
def test_parse_duration(iso_str, expected_seconds):
    assert parse_duration(iso_str) == expected_seconds


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "0:00"),
        (59, "0:59"),
        (60, "1:00"),
        (3661, "1:01:01"),
        (3600, "1:00:00"),
    ],
)
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected
