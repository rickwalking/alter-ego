"""Notifier inputs. The protocol that sends them lives in ``ports``."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from rag_backend.modules.autopilot.domain.cover_offer import CoverOffer
from rag_backend.modules.autopilot.domain.messages import InlineKeyboard
from rag_backend.modules.autopilot.domain.notice_log import NoticeLog


@dataclass(frozen=True, kw_only=True)
class ReviewNotice:
    """One album plus the keyboard message for a revision.

    ``profile`` is the ``Audience · Niche · Style`` line above the caption preview.
    ``fixable`` adds the “Fix issues” button under the quality issue lines.
    ``cover`` drives the GrokBot cover preview and the slide-1 toggle.
    """

    chat_id: str
    run_id: UUID
    title: str
    persona_score: float | None
    sources_count: int
    caption: str
    slide_paths: tuple[str, ...]
    prior_album_ids: tuple[int, ...]
    profile: str = ""
    issues: tuple[str, ...] = ()
    fixable: bool = False
    cover: CoverOffer | None = None


@dataclass(frozen=True, kw_only=True)
class ReviewSendResult:
    """Message ids from the album and the keyboard message."""

    album_ids: tuple[int, ...]
    keyboard_id: int


@dataclass(frozen=True, kw_only=True)
class StatusNotice:
    """A single text message, with a keyboard only when an action is offered.

    When ``photo_path`` is set the notice is sent as a photo with ``text`` as its
    caption.
    """

    chat_id: str
    run_id: UUID
    text: str
    keyboard: InlineKeyboard | None
    photo_path: str | None = None


@dataclass(frozen=True, kw_only=True)
class StatusSendResult:
    """The message id Telegram assigned to a status or reminder."""

    message_id: int


@dataclass(frozen=True, kw_only=True)
class AutopilotOutboxEvent:
    """One committed ``content.autopilot.*`` outbox row."""

    event_id: str
    event_type: str
    run_id: UUID
    payload: Mapping[str, object]
    created_at: datetime


@dataclass(frozen=True, kw_only=True)
class ReviewFacts:
    """Title, caption, and on-disk PT slide paths for one carousel."""

    title: str
    caption: str
    slide_paths: tuple[str, ...]
    audience: str = ""
    niche: str = ""
    image_style: str = ""
    issues: tuple[str, ...] = ()
    fixable: bool = False
    cover: CoverOffer | None = None


@dataclass(frozen=True, kw_only=True)
class SaveNoticeLog:
    """Replace the run's notice ledger without moving ``updated_at``."""

    run_id: UUID
    log: NoticeLog
