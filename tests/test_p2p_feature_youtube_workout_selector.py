"""Tests for youtube_workout_selector entry module."""

import runpy
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENTRY = PROJECT_ROOT / "youtube_workout_selector.py"


def test___main___invokes_workout_gui_main():
    with patch("workout_gui.main") as mock_main:
        runpy.run_path(str(ENTRY), run_name="__main__")
    mock_main.assert_called_once()
