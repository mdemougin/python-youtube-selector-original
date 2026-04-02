"""Failing contract tests until :func:`video_ids_in_all_playlists` is fully implemented."""

from __future__ import annotations

from playlist_intersection import video_ids_in_all_playlists


def test_two_playlists_returns_videos_present_in_both():
    a = ["v1", "v2", "v3"]
    b = ["v2", "v3", "v4"]
    assert video_ids_in_all_playlists((a, b)) == {"v2", "v3"}


def test_three_playlists_returns_videos_present_in_at_least_two():
    assert video_ids_in_all_playlists(
        (
            ["x", "in_two", "in_all"],
            ["in_two", "z", "in_all"],
            ["w", "in_all"],
        )
    ) == {"in_two", "in_all"}


def test_no_shared_videos_returns_empty_set():
    assert video_ids_in_all_playlists((["a", "b"], ["c", "d"])) == set()


def test_identical_playlists_intersection_is_full_set():
    ids = ["z1", "z2", "z3"]
    assert video_ids_in_all_playlists((ids, list(ids))) == {"z1", "z2", "z3"}


def test_duplicates_within_playlist_are_ignored():
    assert video_ids_in_all_playlists(
        (
            ["dup", "dup", "only"],
            ["dup", "other"],
        )
    ) == {"dup"}


def test_any_empty_playlist_makes_intersection_empty():
    assert video_ids_in_all_playlists((["a", "b"], [], ["a"])) == {"a"}


def test_order_of_playlists_does_not_change_result():
    p, q = ["1", "2"], ["2", "3"]
    r1 = video_ids_in_all_playlists((p, q))
    r2 = video_ids_in_all_playlists((q, p))
    assert r1 == r2 == {"2"}
