"""Token source for the Instagram Graph publisher.

The encrypted credential store and test doubles both implement ``get``.
"""

from __future__ import annotations

from typing import Protocol


class InstagramTokenProvider(Protocol):
    """Supplies the current Instagram user access token."""

    async def get(self) -> str:
        """Return the access token, or an empty string when none is configured."""
        ...
