"""Repost draft values, hashing, the idempotency key and owner callbacks. No I/O."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from rag_backend.domain.constants import ENCODING_UTF8
from rag_backend.modules.autopilot.repost_constants import (
    CALLBACK_PATTERN,
    COVER_GROK,
    COVER_ORIGINAL,
    ERR_INVALID_FIELD,
    FIELD_IDEMPOTENCY,
    HTTP_BAD_REQUEST,
    IDEMPOTENCY_PATTERN,
    MESSAGE_BY_CODE,
)

_CALLBACK = re.compile(CALLBACK_PATTERN)
_KEY = re.compile(IDEMPOTENCY_PATTERN)


@dataclass(frozen=True, kw_only=True)
class RepostProblem:
    """A stable code, the HTTP status, and the field that caused it."""

    code: str
    status: int
    field: str | None = None
    message: str | None = None


class RepostError(Exception):
    """A refusal the route turns into ``{"error": {...}}``."""

    def __init__(self, problem: RepostProblem) -> None:
        self.problem = problem
        super().__init__(problem.code)

    @property
    def message(self) -> str:
        """The problem's message, else the default for its code."""
        if self.problem.message:
            return self.problem.message
        return MESSAGE_BY_CODE.get(self.problem.code, self.problem.code)


def invalid(field: str, message: str) -> RepostError:
    """A 400 ``invalid_field`` for ``field``."""
    return RepostError(
        RepostProblem(
            code=ERR_INVALID_FIELD,
            status=HTTP_BAD_REQUEST,
            field=field,
            message=message,
        )
    )


@dataclass(frozen=True, kw_only=True)
class PublishWindow:
    """When the owner wants the repost to go out (UTC)."""

    earliest: datetime
    latest: datetime


@dataclass(frozen=True, kw_only=True)
class RepostDraft:
    """What the scout asked for, after the body was parsed."""

    media_id: str
    caption: str
    hook_text: str | None
    hook_duration_s: float
    trim_start_s: float
    trim_end_s: float | None
    cover_asset_id: UUID | None
    collaborators: tuple[str, ...] | None
    share_to_feed: bool
    reason: str
    score: float | None
    window: PublishWindow | None
    idempotency_key: str


@dataclass(frozen=True, kw_only=True)
class Repost:
    """One stored repost draft and its progress."""

    id: UUID
    idempotency_key: str
    request_hash: str
    media_id: str
    status: str
    permalink: str | None
    caption: str
    hook_text: str | None
    hook_duration_s: float
    trim_start_s: float
    trim_end_s: float | None
    cover_asset_id: UUID | None
    collaborators: tuple[str, ...]
    share_to_feed: bool
    reason: str
    score: float | None
    window: PublishWindow | None
    created_at: datetime
    expires_at: datetime
    cover_choice: str | None = None
    publish_at: datetime | None = None
    approved_at: datetime | None = None
    decided_by: str | None = None
    preview_ready_at: datetime | None = None
    telegram_message_id: int | None = None
    caption_edit_at: datetime | None = None
    container_id: str | None = None
    container_created_at: datetime | None = None
    new_media_id: str | None = None
    new_permalink: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    published_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def default_cover(self) -> str:
        """``grok`` when the draft has a cover asset, else ``original``."""
        return COVER_GROK if self.cover_asset_id is not None else COVER_ORIGINAL


@dataclass(frozen=True, kw_only=True)
class RepostCallback:
    """An owner button: ok, orig, cap or no."""

    action: str
    repost_id: UUID


@dataclass(frozen=True, kw_only=True)
class RepostListQuery:
    """Filters for ``GET /reposts``."""

    statuses: tuple[str, ...]
    since: datetime | None
    limit: int


def request_hash(draft: RepostDraft) -> str:
    """sha256 of the canonical body. The key is not part of it."""
    window = draft.window
    body = {
        "caption": draft.caption,
        "collaborators": None
        if draft.collaborators is None
        else list(draft.collaborators),
        "cover_asset_id": None
        if draft.cover_asset_id is None
        else str(draft.cover_asset_id),
        "earliest": None if window is None else window.earliest.isoformat(),
        "hook_duration_s": draft.hook_duration_s,
        "hook_text": draft.hook_text,
        "latest": None if window is None else window.latest.isoformat(),
        "media_id": draft.media_id,
        "reason": draft.reason,
        "score": draft.score,
        "share_to_feed": draft.share_to_feed,
        "trim_end_s": draft.trim_end_s,
        "trim_start_s": draft.trim_start_s,
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode(ENCODING_UTF8)).hexdigest()


def parse_idempotency_key(value: str | None) -> str:
    """8-128 characters of ``[A-Za-z0-9_-]``, else 400 ``invalid_field``."""
    if value is None or _KEY.fullmatch(value) is None:
        raise invalid(FIELD_IDEMPOTENCY, "8-128 characters of [A-Za-z0-9_-]")
    return value


def parse_repost_callback(data: str) -> RepostCallback | None:
    """None when the button is not a repost callback."""
    match = _CALLBACK.fullmatch(data)
    if match is None:
        return None
    return RepostCallback(action=match.group(1), repost_id=UUID(match.group(2)))


__all__ = [
    "PublishWindow",
    "Repost",
    "RepostCallback",
    "RepostDraft",
    "RepostError",
    "RepostListQuery",
    "RepostProblem",
    "invalid",
    "parse_idempotency_key",
    "parse_repost_callback",
    "request_hash",
]
