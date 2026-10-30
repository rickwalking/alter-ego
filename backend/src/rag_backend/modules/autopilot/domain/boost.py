"""Boost request values, hashing and the owner callback. No I/O."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from rag_backend.domain.constants import ENCODING_UTF8
from rag_backend.modules.autopilot.boost_constants import (
    CALLBACK_BOOST_PATTERN,
    CENTS_PER_UNIT,
    ERR_IDEMPOTENCY_REQUIRED,
    IDEMPOTENCY_MAX,
    IDEMPOTENCY_MIN,
)
from rag_backend.modules.autopilot.domain.ig_media import OpenBoost

_CALLBACK = re.compile(CALLBACK_BOOST_PATTERN)
_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


class BoostError(Exception):
    """A stable code and the HTTP status the route should return."""

    def __init__(self, code: str, status: int) -> None:
        self.code = code
        self.status = status
        super().__init__(code)


class IllegalBoostTransitionError(Exception):
    """The status pair is not in the boost state table."""

    def __init__(self, expected: str, new: str) -> None:
        self.expected = expected
        self.new = new
        super().__init__(f"{expected} -> {new}")


@dataclass(frozen=True, kw_only=True)
class BoostAudience:
    """Countries and an age band. No interests in v1."""

    countries: tuple[str, ...]
    age_min: int
    age_max: int


@dataclass(frozen=True, kw_only=True)
class BoostDraft:
    """What the bot asked for, after the body was parsed."""

    media_id: str
    daily_budget_cents: int
    days: int
    objective: str
    audience: BoostAudience
    reason: str
    score: float | None
    start_at: datetime | None
    idempotency_key: str


@dataclass(frozen=True, kw_only=True)
class BoostRequest:
    """One stored boost request."""

    id: UUID
    idempotency_key: str
    request_hash: str
    media_id: str
    status: str
    objective: str
    daily_budget_cents: int
    days: int
    total_budget_cents: int
    currency: str
    audience: BoostAudience
    reason: str
    score: float | None
    created_at: datetime
    expires_at: datetime
    decided_at: datetime | None = None
    decided_by: str | None = None
    telegram_message_id: int | None = None
    permalink: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    meta_campaign_id: str | None = None
    meta_adset_id: str | None = None
    meta_creative_id: str | None = None
    meta_ad_id: str | None = None
    launch_attempts: int = 0
    next_attempt_at: datetime | None = None
    last_insights: dict[str, int | None] | None = None
    error_code: str | None = None


@dataclass(frozen=True, kw_only=True)
class BoostCallback:
    """An owner button: ok, no, or stop."""

    action: str
    request_id: UUID


@dataclass(frozen=True, kw_only=True)
class MediaEligibility:
    """What ``ig_media`` knows about the post the bot wants to boost."""

    posted_at: datetime | None
    product_type: str | None
    permalink: str | None


@dataclass(frozen=True, kw_only=True)
class StatusSave:
    """The row after a transition, plus the status it left."""

    previous: str
    request: BoostRequest
    actor: str


@dataclass(frozen=True, kw_only=True)
class BoostListQuery:
    """Filters for the list route."""

    statuses: tuple[str, ...]
    media_id: str | None
    limit: int


class CampaignPauser(Protocol):
    """Pauses the live Meta campaign for an owner Stop."""

    async def pause(self, campaign_id: str) -> bool:
        """True when the campaign is paused or there is nothing live to pause."""
        ...


class BoostStore(Protocol):
    """Persistence for requests and the weekly committed total."""

    async def by_key(self, key: str) -> BoostRequest | None:
        """The row for an idempotency key, if any."""
        ...

    async def get(self, request_id: UUID) -> BoostRequest | None:
        """One request."""
        ...

    async def media(self, media_id: str) -> MediaEligibility:
        """Eligibility facts. Missing media has null fields."""
        ...

    async def open_exists(self, media_id: str) -> bool:
        """True when a non-terminal request already targets the media."""
        ...

    async def pending_count(self) -> int:
        """Rows waiting for the owner."""
        ...

    async def committed_cents(self, since: datetime) -> int:
        """Budget cents committed in the rolling window."""
        ...

    async def insert(self, request: BoostRequest) -> None:
        """Store a new pending request and its create event."""
        ...

    async def save_status(self, change: StatusSave) -> None:
        """Replace the row when the status changed, and append an event."""
        ...

    async def list_requests(self, query: BoostListQuery) -> list[BoostRequest]:
        """Newest first."""
        ...

    async def open_for(self, media_ids: tuple[str, ...]) -> dict[str, OpenBoost]:
        """Latest open request per media id."""
        ...

    async def remember_message(self, request_id: UUID, message_id: int) -> None:
        """Store the Telegram message id after the send."""
        ...

    async def commit(self) -> None:
        """Commit the session."""
        ...
        """Latest open request per media id."""
        ...


def request_hash(draft: BoostDraft) -> str:
    """sha256 of the canonical body. Key and timestamps are not part of it."""
    body = {
        "age_max": draft.audience.age_max,
        "age_min": draft.audience.age_min,
        "countries": list(draft.audience.countries),
        "daily_budget_cents": draft.daily_budget_cents,
        "days": draft.days,
        "media_id": draft.media_id,
        "objective": draft.objective,
        "reason": draft.reason,
        "score": draft.score,
        "start_at": None if draft.start_at is None else draft.start_at.isoformat(),
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode(ENCODING_UTF8)).hexdigest()


def parse_idempotency_key(value: str | None) -> str:
    """Require 8-128 url-safe characters."""
    if value is None or not _KEY.fullmatch(value):
        raise BoostError(ERR_IDEMPOTENCY_REQUIRED, 422)
    if len(value) < IDEMPOTENCY_MIN or len(value) > IDEMPOTENCY_MAX:
        raise BoostError(ERR_IDEMPOTENCY_REQUIRED, 422)
    return value


def parse_boost_callback(data: str) -> BoostCallback | None:
    """None when the button is not a boost callback."""
    match = _CALLBACK.fullmatch(data)
    if match is None:
        return None
    return BoostCallback(action=match.group(1), request_id=UUID(match.group(2)))


def format_money(cents: int) -> str:
    """Reais with a comma decimal, for the owner message."""
    whole, frac = divmod(cents, CENTS_PER_UNIT)
    return f"R$ {whole},{frac:02d}"


__all__ = [
    "BoostAudience",
    "BoostCallback",
    "BoostDraft",
    "BoostError",
    "BoostListQuery",
    "BoostRequest",
    "BoostStore",
    "CampaignPauser",
    "IllegalBoostTransitionError",
    "StatusSave",
    "format_money",
    "parse_boost_callback",
    "parse_idempotency_key",
    "request_hash",
]
