"""The slide-1 cover a carousel project renders (ADR-0024).

Set only when the owner chose the GrokBot cover on Telegram; ``None`` keeps the
default slide 1 (the owner's photo on POV, the generated hero on Radar IA).
Stored as one JSON object on ``carousel_projects.slide_cover``.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from rag_backend.domain.constants.slide_cover import (
    COVER_KIND_SCREENSHOT,
    COVER_KINDS,
    SLIDE_COVER_KEY_ASSET_ID,
    SLIDE_COVER_KEY_CREDIT,
    SLIDE_COVER_KEY_KIND,
    SLIDE_COVER_KEY_STAGED_PATH,
)


class CoverAssetError(ValueError):
    """A cover upload breaks a rule; ``code`` is the public contract code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, kw_only=True)
class SlideCover:
    """The creator asset to show, how, where it is staged, and its credit."""

    asset_id: UUID
    kind: str
    staged_path: str
    credit: str = ""

    @property
    def is_screenshot(self) -> bool:
        """True for the framed-card layout (a screenshot, product shot or logo)."""
        return self.kind == COVER_KIND_SCREENSHOT

    def to_row(self) -> dict[str, str]:
        """The JSON object stored on the project."""
        return {
            SLIDE_COVER_KEY_ASSET_ID: str(self.asset_id),
            SLIDE_COVER_KEY_KIND: self.kind,
            SLIDE_COVER_KEY_STAGED_PATH: self.staged_path,
            SLIDE_COVER_KEY_CREDIT: self.credit,
        }


def slide_cover_from_row(raw: object) -> SlideCover | None:
    """The cover stored in ``raw``; None when absent or malformed."""
    if not isinstance(raw, dict):
        return None
    asset_id = _uuid(raw.get(SLIDE_COVER_KEY_ASSET_ID))
    kind = raw.get(SLIDE_COVER_KEY_KIND)
    staged = raw.get(SLIDE_COVER_KEY_STAGED_PATH)
    if asset_id is None or kind not in COVER_KINDS or not isinstance(staged, str):
        return None
    credit = raw.get(SLIDE_COVER_KEY_CREDIT)
    return SlideCover(
        asset_id=asset_id,
        kind=str(kind),
        staged_path=staged,
        credit=credit if isinstance(credit, str) else "",
    )


def slide_cover_row(cover: SlideCover | None) -> dict[str, str] | None:
    """The column value for ``cover`` (NULL when the default slide 1 is used)."""
    if cover is None:
        return None
    return cover.to_row()


def _uuid(value: object) -> UUID | None:
    if not isinstance(value, str):
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


__all__ = ["CoverAssetError", "SlideCover", "slide_cover_from_row", "slide_cover_row"]
