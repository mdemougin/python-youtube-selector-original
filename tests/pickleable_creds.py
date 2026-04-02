"""OAuth-like objects that survive pickle (MagicMock does not)."""

from __future__ import annotations

from typing import Any, Optional


class PickleableCreds:
    """Minimal creds object for youtube_auth tests."""

    def __init__(
        self,
        *,
        valid: bool = True,
        expired: bool = False,
        refresh_token: Optional[str] = "rt",
        fail_refresh: bool = False,
    ) -> None:
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self._fail_refresh = fail_refresh

    def refresh(self, request: Any) -> None:
        if self._fail_refresh:
            from google.auth.exceptions import RefreshError

            raise RefreshError("invalid_grant")
        self.valid = True
        self.expired = False
