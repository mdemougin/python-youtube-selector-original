"""Tests for youtube_api."""

from unittest.mock import MagicMock

import pytest

from youtube_api import (
    fetch_playlist_videos_with_details,
    get_mine_channel_title,
    list_mine_playlists_all_pages,
)


def test_get_mine_channel_title_found():
    youtube = MagicMock()
    youtube.channels.return_value.list.return_value.execute.return_value = {
        "items": [{"snippet": {"title": "Ch"}}]
    }
    assert get_mine_channel_title(youtube) == "Ch"


def test_get_mine_channel_title_empty():
    youtube = MagicMock()
    youtube.channels.return_value.list.return_value.execute.return_value = {}
    assert get_mine_channel_title(youtube) is None


def test_list_mine_playlists_single_page():
    youtube = MagicMock()
    req = youtube.playlists.return_value.list.return_value
    req.execute.return_value = {
        "items": [{"id": "a"}],
        "nextPageToken": None,
    }
    out = list_mine_playlists_all_pages(youtube)
    assert out == [{"id": "a"}]


def test_list_mine_playlists_paginated():
    youtube = MagicMock()

    def list_side_effect(*args, **kwargs):
        m = MagicMock()
        tok = kwargs.get("pageToken")
        if tok is None:
            m.execute.return_value = {
                "items": [{"id": "1"}],
                "nextPageToken": "t2",
            }
        else:
            m.execute.return_value = {
                "items": [{"id": "2"}],
                "nextPageToken": None,
            }
        return m

    youtube.playlists.return_value.list.side_effect = list_side_effect
    out = list_mine_playlists_all_pages(youtube)
    assert [p["id"] for p in out] == ["1", "2"]


def test_list_mine_playlists_page_without_items_key():
    youtube = MagicMock()

    def list_side_effect(*args, **kwargs):
        m = MagicMock()
        m.execute.return_value = {"nextPageToken": None}
        return m

    youtube.playlists.return_value.list.side_effect = list_side_effect
    assert list_mine_playlists_all_pages(youtube) == []


def test_fetch_playlist_videos_skips_empty_video_items():
    youtube = MagicMock()

    pl = youtube.playlistItems.return_value.list.return_value
    pl.execute.return_value = {
        "items": [
            {
                "snippet": {"position": 0},
                "contentDetails": {"videoId": "x"},
            }
        ],
        "nextPageToken": None,
    }

    vid = youtube.videos.return_value.list.return_value
    vid.execute.return_value = {"items": []}

    videos, channels = fetch_playlist_videos_with_details(youtube, "PLx")
    assert videos == []
    assert channels == set()


def test_fetch_playlist_videos_builds_entries_and_pagination():
    youtube = MagicMock()

    pages = [
        {
            "items": [
                {
                    "snippet": {"position": 0},
                    "contentDetails": {"videoId": "a"},
                }
            ],
            "nextPageToken": "n",
        },
        {
            "items": [
                {
                    "snippet": {"position": 1},
                    "contentDetails": {"videoId": "b"},
                }
            ],
            "nextPageToken": None,
        },
    ]

    def pl_list(*args, **kwargs):
        m = MagicMock()
        idx = 0 if kwargs.get("pageToken") is None else 1
        m.execute.return_value = pages[idx]
        return m

    youtube.playlistItems.return_value.list.side_effect = pl_list

    def vid_list(*args, **kwargs):
        m = MagicMock()
        vid = kwargs.get("id")
        m.execute.return_value = {
            "items": [
                {
                    "snippet": {
                        "title": f"T-{vid}",
                        "channelTitle": f"C-{vid}",
                        "thumbnails": {"medium": {"url": f"http://t/{vid}"}},
                    },
                    "contentDetails": {"duration": "PT3M"},
                }
            ]
        }
        return m

    youtube.videos.return_value.list.side_effect = vid_list

    videos, channels = fetch_playlist_videos_with_details(youtube, "PLid")
    assert len(videos) == 2
    assert videos[0]["id"] == "a"
    assert videos[0]["position"] == 1
    assert videos[1]["position"] == 2
    assert channels == {"C-a", "C-b"}
