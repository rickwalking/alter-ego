"""The POV thesis step of an autopilot run (ADR-0021 D10). No I/O.

A POV topic carries the scout's DRAFT thesis. The run waits in
``awaiting_thesis`` until the owner confirms it, replaces it with their own
text, or discards the topic; only then does generation start.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from rag_backend.domain.content_mode import is_pov_family, is_pov_news
from rag_backend.modules.autopilot.domain.cover_offer import CoverOffer, with_cover_row
from rag_backend.modules.autopilot.domain.messages import (
    InlineButton,
    InlineKeyboard,
    callback_data,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    ThesisConfirmCommand,
    TopicCandidate,
)
from rag_backend.modules.autopilot.pov_constants import (
    BUTTON_THESIS_CONFIRM,
    BUTTON_THESIS_DISCARD,
    BUTTON_THESIS_EDIT,
    CALLBACK_THESIS_CONFIRM_PREFIX,
    CALLBACK_THESIS_DISCARD_PREFIX,
    CALLBACK_THESIS_EDIT_PREFIX,
    CALLBACK_THESIS_PATTERN,
    MODE_LABEL_POV,
    MODE_LABEL_POV_NEWS,
    TEXT_THESIS_PROMPT,
    THESIS_DRAFT_MAX_CHARS,
)

_THESIS_CALLBACK = re.compile(CALLBACK_THESIS_PATTERN)
THESIS_NOTICE_KEY = "thesis:{run_id}"


@dataclass(frozen=True, kw_only=True)
class ThesisCallback:
    """One thesis button: ``thok`` / ``thed`` / ``thno`` and the run."""

    kind: str
    run_id: UUID


def is_pov(topic: TopicCandidate) -> bool:
    """True for a POV-family topic (``pov`` and ``pov_news``)."""
    return is_pov_family(topic.content_mode)


def needs_thesis(run: AutopilotRun, topic: TopicCandidate) -> bool:
    """A POV run without a confirmed thesis must not start generating."""
    return is_pov(topic) and not run.pov_thesis


def clean_thesis(text: str) -> str | None:
    """The owner's thesis, single-spaced, or None when blank or too long."""
    cleaned = " ".join(text.split())
    if not cleaned or len(cleaned) > THESIS_DRAFT_MAX_CHARS:
        return None
    return cleaned


def parse_thesis_callback(data: str) -> ThesisCallback | None:
    """``ap:thok|thed|thno:<uuid>``; anything else is None."""
    match = _THESIS_CALLBACK.fullmatch(data)
    if match is None:
        return None
    return ThesisCallback(kind=match.group(1), run_id=UUID(match.group(2)))


def thesis_keyboard(run_id: UUID, cover: CoverOffer | None = None) -> InlineKeyboard:
    """Confirm, Edit and Discard for one run (each callback <=64 bytes).

    A topic with a GrokBot cover adds the slide-1 toggle row.
    """
    row = (
        InlineButton(
            text=BUTTON_THESIS_CONFIRM,
            callback_data=callback_data(CALLBACK_THESIS_CONFIRM_PREFIX, run_id),
        ),
        InlineButton(
            text=BUTTON_THESIS_EDIT,
            callback_data=callback_data(CALLBACK_THESIS_EDIT_PREFIX, run_id),
        ),
        InlineButton(
            text=BUTTON_THESIS_DISCARD,
            callback_data=callback_data(CALLBACK_THESIS_DISCARD_PREFIX, run_id),
        ),
    )
    return with_cover_row(InlineKeyboard(rows=(row,)), run_id, cover)


def thesis_prompt_text(topic: TopicCandidate) -> str:
    """The Telegram prompt with the mode, the topic title and the scout's draft."""
    mode = MODE_LABEL_POV_NEWS if is_pov_news(topic.content_mode) else MODE_LABEL_POV
    return TEXT_THESIS_PROMPT.format(
        mode=mode, title=topic.title, thesis=topic.thesis_draft or ""
    )


def thesis_notice_key(run_id: UUID) -> str:
    """The notice-ledger key that marks the prompt as sent."""
    return THESIS_NOTICE_KEY.format(run_id=run_id)


__all__ = [
    "ThesisCallback",
    "ThesisConfirmCommand",
    "clean_thesis",
    "is_pov",
    "needs_thesis",
    "parse_thesis_callback",
    "thesis_keyboard",
    "thesis_notice_key",
    "thesis_prompt_text",
]
