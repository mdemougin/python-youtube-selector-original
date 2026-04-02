"""Shared test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def png_bytes() -> bytes:
    """Minimal PNG bytes for mocking HTTP thumbnail responses."""
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (220, 160), color=(128, 64, 32)).save(buf, format="PNG")
    return buf.getvalue()


def make_youtube_mock(
    *,
    channel_title: str | None = "My Channel",
    playlists: list | None = None,
    playlist_items_pages: list | None = None,
    video_by_id: dict | None = None,
):
    """
    Build a MagicMock youtube service with chained list().execute() responses.

    playlist_items_pages: list of dicts, each the return value of playlistItems.list execute().
    video_by_id: map videoId -> videos.list execute response body.
    """
    from unittest.mock import MagicMock

    youtube = MagicMock()

    ch = youtube.channels.return_value.list.return_value
    if channel_title is None:
        ch.execute.return_value = {"items": []}
    else:
        ch.execute.return_value = {
            "items": [{"snippet": {"title": channel_title}}]
        }

    pl_list = playlists if playlists is not None else _default_playlists()
    pl_pages = _paginate_playlists(pl_list)

    def playlists_list_side_effect(*args, **kwargs):
        m = MagicMock()
        token = kwargs.get("pageToken")
        idx = 0 if not token else int(str(token))
        page = pl_pages[idx]
        m.execute.return_value = page
        return m

    youtube.playlists.return_value.list.side_effect = playlists_list_side_effect

    pages = (
        playlist_items_pages
        if playlist_items_pages is not None
        else _default_playlist_items_pages()
    )
    vmap = video_by_id if video_by_id is not None else {}

    def playlist_items_list_side_effect(*args, **kwargs):
        m = MagicMock()
        token = kwargs.get("pageToken")
        idx = 0 if not token else int(str(token))
        m.execute.return_value = pages[idx]
        return m

    youtube.playlistItems.return_value.list.side_effect = playlist_items_list_side_effect

    def videos_list_side_effect(*args, **kwargs):
        m = MagicMock()
        vid = kwargs.get("id")
        m.execute.return_value = vmap.get(vid, _default_video_response(vid))
        return m

    youtube.videos.return_value.list.side_effect = videos_list_side_effect

    return youtube


def _default_playlists():
    return [
        _pl("p1", "Short Public", "public", 2, thumb="medium"),
        _pl("p2", "Private List", "private", 1, thumb="default"),
        _pl("p3", "Unlisted List", "unlisted", 1, thumb="none"),
        _pl("p4", "Empty Skip", "public", 0, thumb="medium"),
        _pl("p5", "Long Title " * 10, "public", 1, thumb="medium"),
        _pl("p6", "Weird Privacy", "internal", 1, thumb="medium"),
    ]


def _pl(pid, title, privacy, count, thumb="medium"):
    th = {}
    if thumb == "medium":
        th["medium"] = {"url": "http://example.com/m.jpg"}
    elif thumb == "default":
        th["default"] = {"url": "http://example.com/d.jpg"}
    return {
        "id": pid,
        "snippet": {"title": title, "thumbnails": th},
        "contentDetails": {"itemCount": count},
        "status": {"privacyStatus": privacy},
    }


def _paginate_playlists(items, page_size=50):
    pages = []
    for i in range(0, len(items), page_size):
        chunk = items[i : i + page_size]
        nxt = None
        if i + page_size < len(items):
            nxt = str(i // page_size + 1)
        pages.append({"items": chunk, "nextPageToken": nxt})
    if not pages:
        pages.append({"items": []})
    return pages


def _default_playlist_items_pages():
    return [
        {
            "items": [
                _pli("v1", 0, "PT5M"),
                _pli("v2", 1, "PT10M"),
            ],
            "nextPageToken": "1",
        },
        {
            "items": [_pli("v3", 2, "PT1H")],
            "nextPageToken": None,
        },
    ]


def _pli(vid, position, iso_duration):
    return {
        "snippet": {"position": position},
        "contentDetails": {"videoId": vid},
    }


def _default_video_response(vid):
    return {
        "items": [
            {
                "snippet": {
                    "title": f"Video {vid}",
                    "channelTitle": f"Channel {vid}",
                    "thumbnails": {"medium": {"url": "http://thumb.example/t.png"}},
                },
                "contentDetails": {"duration": "PT5M30S"},
            }
        ]
    }
