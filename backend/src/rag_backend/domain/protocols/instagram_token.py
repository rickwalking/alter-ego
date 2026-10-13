"""Token source for the Instagram Graph publisher.

AE-0358 replaces the settings-backed adapter with the encrypted credential
store. Both call ``get``.
"""

from __future__ import annotations

from typing import Protocol


class InstagramTokenProvider(Protocol):
    """Supplies the current Instagram user access token."""

    async def get(self) -> str:
        """Return the access token, or an empty string when none is configured."""
        ...
