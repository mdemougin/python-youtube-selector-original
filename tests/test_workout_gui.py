"""Tests for workout_gui (UI logic with Tk fully mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from tests.conftest import make_youtube_mock
from tests.tk_harness import apply_workout_gui_tk_patches


@pytest.fixture
def mock_root():
    return MagicMock()


@pytest.fixture
def patch_gui_deps(mock_root, mocker, png_bytes):
    apply_workout_gui_tk_patches(mocker, mock_root)
    yt = make_youtube_mock()

    def ok_get(url, **kwargs):
        r = MagicMock()
        r.content = png_bytes
        return r

    mocker.patch("workout_gui.build_youtube_service", return_value=yt)
    mocker.patch("workout_gui.requests.get", side_effect=ok_get)
    mocker.patch("workout_gui.messagebox.showinfo")
    mocker.patch("workout_gui.messagebox.showerror")
    mocker.patch("workout_gui.messagebox.showwarning")
    mocker.patch("workout_gui.webbrowser.open")

    from workout_gui import YouTubePlaylistSelector

    app = YouTubePlaylistSelector(mock_root)
    return app, yt


def test_load_playlists_youtube_none(mock_root, mocker):
    apply_workout_gui_tk_patches(mocker, mock_root)
    mocker.patch("workout_gui.build_youtube_service", return_value=None)
    from workout_gui import YouTubePlaylistSelector

    app = YouTubePlaylistSelector(mock_root)
    app.load_playlists()


def test_load_playlists_clears_existing_playlist_widgets(patch_gui_deps):
    app, _ = patch_gui_deps
    child = MagicMock()
    app.playlists_frame.winfo_children = MagicMock(return_value=[child])
    app.load_playlists()
    # Cleared at start of load_playlists and again inside display_playlists.
    assert child.destroy.call_count >= 1


def test_load_playlists_success_and_filtered_label(patch_gui_deps):
    app, _ = patch_gui_deps
    assert hasattr(app, "all_playlists")
    assert "Loaded" in app.loading_label.cget("text")
    app.show_private.set(False)
    app.display_playlists()
    assert "showing" in app.loading_label.cget("text")


def test_load_playlists_no_channel_title(mock_root, mocker, png_bytes):
    apply_workout_gui_tk_patches(mocker, mock_root)
    yt = make_youtube_mock()
    mocker.patch("workout_gui.build_youtube_service", return_value=yt)
    mocker.patch("workout_gui.get_mine_channel_title", return_value=None)
    mocker.patch(
        "workout_gui.requests.get",
        side_effect=lambda *a, **k: MagicMock(content=png_bytes),
    )
    from workout_gui import YouTubePlaylistSelector

    YouTubePlaylistSelector(mock_root)


def test_load_playlists_empty_account(mock_root, mocker, png_bytes):
    apply_workout_gui_tk_patches(mocker, mock_root)
    yt = make_youtube_mock()
    yt.playlists.return_value.list.side_effect = None
    yt.playlists.return_value.list.return_value.execute.return_value = {
        "items": [],
        "nextPageToken": None,
    }

    mocker.patch("workout_gui.build_youtube_service", return_value=yt)
    mocker.patch(
        "workout_gui.requests.get",
        side_effect=lambda *a, **k: MagicMock(content=png_bytes),
    )
    mocker.patch("workout_gui.messagebox.showinfo")
    from workout_gui import YouTubePlaylistSelector

    app = YouTubePlaylistSelector(mock_root)
    app.load_playlists()


def test_load_playlists_http_error(mock_root, mocker, png_bytes):
    apply_workout_gui_tk_patches(mocker, mock_root)
    yt = make_youtube_mock()
    yt.channels.return_value.list.return_value.execute.side_effect = HttpError(
        MagicMock(status=403), b"{}"
    )

    mocker.patch("workout_gui.build_youtube_service", return_value=yt)
    mocker.patch(
        "workout_gui.requests.get",
        side_effect=lambda *a, **k: MagicMock(content=png_bytes),
    )
    mocker.patch("workout_gui.messagebox.showerror")
    from workout_gui import YouTubePlaylistSelector

    app = YouTubePlaylistSelector(mock_root)
    app.load_playlists()


def test_filter_playlists_without_all_playlists(mock_root, mocker, png_bytes):
    apply_workout_gui_tk_patches(mocker, mock_root)
    mocker.patch("workout_gui.build_youtube_service", return_value=make_youtube_mock())
    mocker.patch(
        "workout_gui.requests.get",
        side_effect=lambda *a, **k: MagicMock(content=png_bytes),
    )
    from workout_gui import YouTubePlaylistSelector

    app = YouTubePlaylistSelector(mock_root)
    app.filter_playlists()


def test_filter_playlists_calls_display(patch_gui_deps):
    app, _ = patch_gui_deps
    app.display_playlists = MagicMock()
    app.filter_playlists()
    app.display_playlists.assert_called_once()


def test_display_playlists_loading_label_no_loaded_prefix(mock_root, mocker, png_bytes):
    apply_workout_gui_tk_patches(mocker, mock_root)
    mocker.patch("workout_gui.build_youtube_service", return_value=make_youtube_mock())
    mocker.patch(
        "workout_gui.requests.get",
        side_effect=lambda *a, **k: MagicMock(content=png_bytes),
    )
    from workout_gui import YouTubePlaylistSelector

    app = YouTubePlaylistSelector(mock_root)
    app.all_playlists = [
        {
            "id": "z",
            "snippet": {"title": "T", "thumbnails": {"medium": {"url": ""}}},
            "contentDetails": {"itemCount": 1},
            "status": {"privacyStatus": "public"},
        }
    ]
    app.loading_label.config(text="Something else")
    app.display_playlists()


def test_privacy_filters_hide_playlists(patch_gui_deps):
    app, _ = patch_gui_deps
    app.show_public.set(False)
    app.show_private.set(False)
    app.show_unlisted.set(False)
    app.display_playlists()


def test_thumbnail_request_fails(patch_gui_deps, mocker):
    app, _ = patch_gui_deps
    mocker.patch("workout_gui.requests.get", side_effect=OSError("network"))
    app.display_playlists()


def test_on_channel_filter_selected(patch_gui_deps):
    app, _ = patch_gui_deps
    app.channel_filter_var.set("ChA")
    app.on_channel_filter_selected(MagicMock())
    app.channel_filter_var.set("All Channels")
    app.on_channel_filter_selected(MagicMock())


def test_select_playlist_youtube_none(mock_root, mocker):
    apply_workout_gui_tk_patches(mocker, mock_root)
    mocker.patch("workout_gui.build_youtube_service", return_value=None)
    from workout_gui import YouTubePlaylistSelector

    app = YouTubePlaylistSelector(mock_root)
    app.select_playlist("x")


def test_select_load_videos_and_cache(patch_gui_deps):
    app, _ = patch_gui_deps
    pid = next(iter(app.playlists))
    app.select_playlist(pid)
    assert pid in app.playlist_videos
    app.select_playlist(pid)


def test_select_playlist_clears_video_info_children(patch_gui_deps, mocker):
    app, _ = patch_gui_deps
    pid = next(iter(app.playlists))
    old = MagicMock()
    app.video_info_frame.winfo_children = MagicMock(return_value=[old])
    app.select_playlist(pid)
    old.destroy.assert_called_once()


def test_load_playlist_videos_http_error(patch_gui_deps, mocker):
    app, _ = patch_gui_deps

    def boom(*a, **k):
        raise HttpError(MagicMock(status=500), b"{}")

    mocker.patch("workout_gui.fetch_playlist_videos_with_details", side_effect=boom)
    pid = next(iter(app.playlists))
    app.select_playlist(pid)


def test_load_playlist_videos_youtube_none(mock_root, mocker):
    apply_workout_gui_tk_patches(mocker, mock_root)
    mocker.patch("workout_gui.build_youtube_service", return_value=None)
    from workout_gui import YouTubePlaylistSelector

    app = YouTubePlaylistSelector(mock_root)
    app.youtube = None
    app.load_playlist_videos("any")


def test_update_playlist_stats_branches(patch_gui_deps):
    app, _ = patch_gui_deps
    pid = next(iter(app.playlists))
    app.selected_playlist_id = pid
    app.playlist_videos[pid] = [
        {"channel": "A", "title": "t", "duration": 1, "duration_str": "0:01"},
        {"channel": "B", "title": "t2", "duration": 2, "duration_str": "0:02"},
    ]
    app.playlists[pid]["title"] = "Pl"
    app.update_playlist_stats()

    app.playlist_videos[pid] = [
        {"channel": "A", "title": "t", "duration": 1, "duration_str": "0:01"},
    ]
    app.update_playlist_stats()

    app.selected_playlist_id = None
    app.update_playlist_stats()


def test_select_random_video_early_exit(patch_gui_deps):
    app, _ = patch_gui_deps
    app.select_random_video()


def test_select_random_video_invalid_inputs(patch_gui_deps):
    app, _ = patch_gui_deps
    import tkinter as tk

    pid = next(iter(app.playlists))
    app.select_playlist(pid)
    app.min_duration_input.insert(0, "x")
    app.select_random_video()
    app.min_duration_input.delete(0, tk.END)
    app.max_duration_input.insert(0, "y")
    app.select_random_video()
    app.max_duration_input.delete(0, tk.END)
    app.min_duration_input.insert(0, "10")
    app.max_duration_input.insert(0, "5")
    app.select_random_video()


def test_select_random_video_no_match_messages(patch_gui_deps):
    app, _ = patch_gui_deps
    pid = next(iter(app.playlists))
    app.select_playlist(pid)
    app.playlist_videos[pid] = [
        {
            "id": "1",
            "title": "t",
            "channel": "OnlyChannel",
            "duration": 120,
            "duration_str": "2:00",
            "position": 1,
        }
    ]
    app.min_duration_input.insert(0, "999")
    app.max_duration_input.insert(0, "9999")
    app.channel_filter_input.insert(0, "nope")
    app.select_random_video()

    app.channel_filter_input.delete(0, "end")
    app.select_random_video()

    app.playlist_videos[pid] = []
    app.min_duration_input.delete(0, "end")
    app.max_duration_input.delete(0, "end")
    app.select_random_video()


def test_select_random_video_many_channels_suggestion(patch_gui_deps):
    app, _ = patch_gui_deps
    pid = next(iter(app.playlists))
    app.select_playlist(pid)
    vids = []
    for i in range(12):
        vids.append(
            {
                "id": str(i),
                "title": "t",
                "channel": f"ChannelNumber{i}",
                "duration": 120,
                "duration_str": "2:00",
                "position": i + 1,
            }
        )
    app.playlist_videos[pid] = vids
    app.min_duration_input.insert(0, "1")
    app.max_duration_input.insert(0, "3")
    app.channel_filter_input.insert(0, "zzznomatch")
    app.select_random_video()


def test_select_random_video_channel_filter_no_duration_matches(patch_gui_deps):
    app, _ = patch_gui_deps
    pid = next(iter(app.playlists))
    app.select_playlist(pid)
    app.playlist_videos[pid] = [
        {
            "id": "1",
            "title": "t",
            "channel": "Zed",
            "duration": 10,
            "duration_str": "0:10",
            "position": 1,
        }
    ]
    app.min_duration_input.insert(0, "999")
    app.max_duration_input.insert(0, "1000")
    app.channel_filter_input.insert(0, "Zed")
    app.select_random_video()


def test_select_random_video_success(patch_gui_deps, mocker):
    app, _ = patch_gui_deps
    pid = next(iter(app.playlists))
    app.select_playlist(pid)
    app.playlist_videos[pid] = [
        {
            "id": "v99",
            "title": "Pick me",
            "channel": "C",
            "duration": 300,
            "duration_str": "5:00",
            "position": 3,
        }
    ]
    mocker.patch("workout_gui.random.choice", side_effect=lambda seq: seq[0])
    app.select_random_video()


def test_display_video_info_thumb_fail(patch_gui_deps, mocker):
    app, _ = patch_gui_deps
    mocker.patch("workout_gui.requests.get", side_effect=OSError("fail"))
    app.display_video_info(
        {
            "id": "x",
            "title": "T",
            "channel": "C",
            "duration_str": "1:00",
            "position": 1,
            "thumbnail": "http://x",
        }
    )


def test_display_video_info_clears_children(patch_gui_deps, mocker, png_bytes):
    app, _ = patch_gui_deps
    prev = MagicMock()
    app.video_info_frame.winfo_children = MagicMock(return_value=[prev])
    mocker.patch(
        "workout_gui.requests.get",
        side_effect=lambda *a, **k: MagicMock(content=png_bytes),
    )
    app.display_video_info(
        {
            "id": "openme",
            "title": "T",
            "channel": "C",
            "duration_str": "1:00",
            "position": 1,
            "thumbnail": "http://x",
        }
    )
    prev.destroy.assert_called_once()


def test_display_video_info_success(patch_gui_deps, mocker, png_bytes):
    app, _ = patch_gui_deps
    mocker.patch(
        "workout_gui.requests.get",
        side_effect=lambda *a, **k: MagicMock(content=png_bytes),
    )
    app.display_video_info(
        {
            "id": "openme",
            "title": "T",
            "channel": "C",
            "duration_str": "1:00",
            "position": 1,
            "thumbnail": "http://x",
        }
    )


def test_main_invokes_tk(mocker):
    mock_root = MagicMock()
    mocker.patch("workout_gui.tk.Tk", return_value=mock_root)
    mocker.patch("workout_gui.YouTubePlaylistSelector")
    from workout_gui import main

    main()
    mock_root.mainloop.assert_called_once()
