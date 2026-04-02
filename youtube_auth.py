"""OAuth2 setup and YouTube API v3 client construction."""

import os
import pickle
import tkinter as tk
from tkinter import messagebox
from typing import Any, Optional

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube",
]


def _run_installed_flow(root: tk.Misc) -> Optional[Any]:
    if not os.path.exists("client_secrets.json"):
        messagebox.showinfo(
            "Setup Required",
            "Please follow these steps:\n\n"
            "1. Go to Google Cloud Console\n"
            "2. Create OAuth2 credentials (Desktop application)\n"
            "3. Download the credentials as 'client_secrets.json'\n"
            "4. Place it in the same folder as this script\n"
            "5. Run the script again",
        )
        root.quit()
        return None
    flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
    return flow.run_local_server(port=0)


def build_youtube_service(root: tk.Misc) -> Optional[Any]:
    """
    Load or obtain OAuth credentials and return a YouTube API v3 service.

    Returns None if setup is incomplete (app will quit after showing a dialog).
    """
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if creds and creds.valid:
        return build("youtube", "v3", credentials=creds)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            creds = None
            try:
                os.remove("token.pickle")
            except OSError:
                pass

    if creds and creds.valid:
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
        return build("youtube", "v3", credentials=creds)

    creds = _run_installed_flow(root)
    if creds is None:
        return None

    with open("token.pickle", "wb") as token:
        pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)
