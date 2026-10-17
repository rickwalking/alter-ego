"""The owner's slide-1 choice on Telegram (AE-0418, ADR-0024). No I/O.

When a run's topic carries a GrokBot cover, the thesis message (POV modes) and
the review message (every mode) show the cover and a toggle: "Usar capa do
Grok" switches slide 1 to it; "Usar minha foto" (POV) / "Usar capa padrão"
(Radar IA) switches back. The default is always the usual slide 1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from rag_backend.domain.constants.slide_cover import COVER_KIND_SCREENSHOT
from rag_backend.modules.autopilot.cover_constants import (
    BUTTON_COVER_OFF_NEWS,
    BUTTON_COVER_OFF_POV,
    BUTTON_COVER_ON,
    CALLBACK_COVER_OFF_PREFIX,
    CALLBACK_COVER_ON_PREFIX,
    CALLBACK_COVER_PATTERN,
    CAPTION_COVER_AI_IMAGE,
    CAPTION_COVER_SCREENSHOT,
    COVER_NOTICE_KEY,
    KIND_COVER_ON,
)
from rag_backend.modules.autopilot.domain.messages import (
    InlineButton,
    InlineKeyboard,
    callback_data,
)

_COVER_CALLBACK = re.compile(CALLBACK_COVER_PATTERN)


@dataclass(frozen=True, kw_only=True)
class CoverOffer:
    """A run's GrokBot cover: kind, credit, the owner's choice, preview file."""

    kind: str
    credit: str
    chosen: bool
    pov: bool
    photo_path: str


@dataclass(frozen=True, kw_only=True)
class CoverCallback:
    """One cover tap: use the cover (``on``) or the default, and the run."""

    use_cover: bool
    run_id: UUID


def parse_cover_callback(data: str) -> CoverCallback | None:
    """``ap:cv:<uuid>`` / ``ap:cvoff:<uuid>``; anything else is None."""
    match = _COVER_CALLBACK.fullmatch(data)
    if match is None:
        return None
    return CoverCallback(
        use_cover=match.group(1) == KIND_COVER_ON, run_id=UUID(match.group(2))
    )


def cover_button(run_id: UUID, offer: CoverOffer) -> InlineButton:
    """The toggle: the cover when the default is shown, else back to default."""
    if not offer.chosen:
        return InlineButton(
            text=BUTTON_COVER_ON,
            callback_data=callback_data(CALLBACK_COVER_ON_PREFIX, run_id),
        )
    return InlineButton(
        text=BUTTON_COVER_OFF_POV if offer.pov else BUTTON_COVER_OFF_NEWS,
        callback_data=callback_data(CALLBACK_COVER_OFF_PREFIX, run_id),
    )


def with_cover_row(
    keyboard: InlineKeyboard, run_id: UUID, offer: CoverOffer | None
) -> InlineKeyboard:
    """``keyboard`` plus the toggle on its own last row (no offer: unchanged)."""
    if offer is None:
        return keyboard
    return InlineKeyboard(rows=(*keyboard.rows, (cover_button(run_id, offer),)))


def cover_caption(offer: CoverOffer) -> str:
    """The caption of the cover preview photo."""
    if offer.kind == COVER_KIND_SCREENSHOT:
        return CAPTION_COVER_SCREENSHOT.format(credit=offer.credit)
    return CAPTION_COVER_AI_IMAGE


def cover_notice_key(scope: str, run_id: UUID) -> str:
    """The notice-ledger key that marks one cover preview as sent."""
    return COVER_NOTICE_KEY.format(scope=scope, run_id=run_id)


def chosen_as(offer: CoverOffer, *, chosen: bool) -> CoverOffer:
    """The same offer after the owner's tap."""
    return CoverOffer(
        kind=offer.kind,
        credit=offer.credit,
        chosen=chosen,
        pov=offer.pov,
        photo_path=offer.photo_path,
    )


__all__ = [
    "CoverCallback",
    "CoverOffer",
    "chosen_as",
    "cover_button",
    "cover_caption",
    "cover_notice_key",
    "parse_cover_callback",
    "with_cover_row",
]
