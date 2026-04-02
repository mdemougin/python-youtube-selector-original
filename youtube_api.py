"""YouTube Data API calls used by the workout selector (no UI)."""

from typing import Any, Dict, List, Optional, Set, Tuple

from duration_utils import format_duration, parse_duration


def get_mine_channel_title(youtube: Any) -> Optional[str]:
    """Return the authenticated user's channel title, or None if unavailable."""
    channel_response = (
        youtube.channels().list(part="snippet", mine=True).execute()
    )
    items = channel_response.get("items")
    if items:
        return items[0]["snippet"]["title"]
    return None


def list_mine_playlists_all_pages(youtube: Any) -> List[Dict[str, Any]]:
    """Fetch all playlists for the authenticated user (paginated)."""
    playlists: List[Dict[str, Any]] = []
    next_page_token = None
    while True:
        request = youtube.playlists().list(
            part="snippet,contentDetails,status",
            mine=True,
            maxResults=50,
            pageToken=next_page_token,
        )
        response = request.execute()
        if "items" in response:
            playlists.extend(response["items"])
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
    return playlists


def fetch_playlist_videos_with_details(
    youtube: Any, playlist_id: str
) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """
    Load all items in a playlist with full video details (duration, channel, etc.).

    Returns (videos, channel_titles) where each video dict matches the GUI expectations.
    """
    videos: List[Dict[str, Any]] = []
    channels_set: Set[str] = set()
    next_page_token = None

    while True:
        response = (
            youtube.playlistItems()
            .list(
                part="snippet,contentDetails",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token,
            )
            .execute()
        )

        for item in response["items"]:
            video_id = item["contentDetails"]["videoId"]
            video_response = (
                youtube.videos()
                .list(part="snippet,contentDetails", id=video_id)
                .execute()
            )

            if not video_response["items"]:
                continue

            video_data = video_response["items"][0]
            duration_sec = parse_duration(video_data["contentDetails"]["duration"])
            channel_title = video_data["snippet"]["channelTitle"]

            videos.append(
                {
                    "id": video_id,
                    "title": video_data["snippet"]["title"],
                    "channel": channel_title,
                    "thumbnail": video_data["snippet"]["thumbnails"]["medium"]["url"],
                    "duration": duration_sec,
                    "duration_str": format_duration(duration_sec),
                    "position": item["snippet"]["position"] + 1,
                }
            )
            channels_set.add(channel_title)

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return videos, channels_set
