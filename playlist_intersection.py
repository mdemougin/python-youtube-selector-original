"""Playlist comparison (stub). Implement :func:`video_ids_in_all_playlists` for full behavior."""

from __future__ import annotations

from collections.abc import Collection, Sequence

__all__ = ["video_ids_in_all_playlists"]


def video_ids_in_all_playlists(playlists: Sequence[Collection[str]]) -> set[str]:
    """Stub: validation only; intersection logic not implemented yet."""
    if len(playlists) < 2:
        raise ValueError("At least two playlists are required to compare.")
    _ = playlists
    return {"__NOT_IMPLEMENTED__"}
