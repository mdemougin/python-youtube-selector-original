"""Passing contract tests for playlist comparison (validation only)."""

from __future__ import annotations

import pytest

from playlist_intersection import video_ids_in_all_playlists


def test_requires_at_least_two_playlists_empty_input():
    with pytest.raises(ValueError, match="2|two|least"):
        video_ids_in_all_playlists(())


def test_requires_at_least_two_playlists_single_playlist():
    with pytest.raises(ValueError, match="2|two|least"):
        video_ids_in_all_playlists((["a", "b"],))
