"""Request and response models for POST /api/autopilot/topics.

``extra=forbid`` rejects scout fields the contract does not name. Source
values must be http(s) URLs. Length limits match the ticket.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from rag_backend.modules.autopilot.constants import (
    ANGLE_MAX_CHARS,
    AUDIENCE_MAX_CHARS,
    BRIEF_MAX_CHARS,
    METRIC_MIN,
    NICHE_MAX_CHARS,
    SCORE_MAX,
    SCORE_MIN,
    SCOUT_REASON_MAX_CHARS,
    SOURCE_URL_INVALID,
    SOURCE_URL_MAX,
    SOURCE_URL_MIN,
    TEXT_MIN_CHARS,
    TITLE_MAX_CHARS,
    TOPIC_BATCH_MAX,
    TOPIC_BATCH_MIN,
    URL_MAX_CHARS,
    WHY_VIRAL_MAX_CHARS,
    X_HANDLE_MAX_CHARS,
    X_POST_TEXT_MAX_CHARS,
    X_SIGNAL_BATCH_MAX,
    X_SIGNAL_BATCH_MIN,
)
from rag_backend.modules.autopilot.domain.topic_text import is_http_url, strip_controls


class TopicProposal(BaseModel):
    """One scout proposal. Unknown keys are a 422 for the whole batch."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=TEXT_MIN_CHARS, max_length=TITLE_MAX_CHARS)
    angle: str = Field(min_length=TEXT_MIN_CHARS, max_length=ANGLE_MAX_CHARS)
    why_viral: str = Field(min_length=TEXT_MIN_CHARS, max_length=WHY_VIRAL_MAX_CHARS)
    audience: str = Field(min_length=TEXT_MIN_CHARS, max_length=AUDIENCE_MAX_CHARS)
    niche: str = Field(min_length=TEXT_MIN_CHARS, max_length=NICHE_MAX_CHARS)
    brief: str = Field(min_length=TEXT_MIN_CHARS, max_length=BRIEF_MAX_CHARS)
    sources: list[Annotated[str, Field(max_length=URL_MAX_CHARS)]] = Field(
        min_length=SOURCE_URL_MIN, max_length=SOURCE_URL_MAX
    )
    score: int = Field(ge=SCORE_MIN, le=SCORE_MAX)

    @field_validator("sources")
    @classmethod
    def sources_are_http_urls(cls, value: list[str]) -> list[str]:
        """Reject a batch whose sources are not http(s) URLs."""
        return [_require_http_url(item) for item in value]


class TopicBatch(BaseModel):
    """One to three proposals. The body is an object, not a bare array."""

    model_config = ConfigDict(extra="forbid")

    topics: list[TopicProposal] = Field(
        min_length=TOPIC_BATCH_MIN,
        max_length=TOPIC_BATCH_MAX,
    )


class RejectedTopic(BaseModel):
    """A proposal the intake did not queue, with a stable reason code."""

    model_config = ConfigDict(extra="forbid")

    title: str
    reason: str


class TopicIntakeResponse(BaseModel):
    """Accepted candidate ids, queued run ids, and per-proposal rejections."""

    model_config = ConfigDict(extra="forbid")

    accepted: list[UUID]
    queued: list[UUID]
    rejected: list[RejectedTopic]


class ObservedXPost(BaseModel):
    """One browser observation. Unknown keys reject the whole body."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=TEXT_MIN_CHARS, max_length=URL_MAX_CHARS)
    handle: str = Field(min_length=TEXT_MIN_CHARS, max_length=X_HANDLE_MAX_CHARS)
    text: str = Field(min_length=TEXT_MIN_CHARS, max_length=X_POST_TEXT_MAX_CHARS)
    likes: int | None = Field(default=None, ge=METRIC_MIN)
    reposts: int | None = Field(default=None, ge=METRIC_MIN)
    replies: int | None = Field(default=None, ge=METRIC_MIN)
    views: int | None = Field(default=None, ge=METRIC_MIN)
    observed_at: datetime


class XSignalsBatch(BaseModel):
    """One to thirty observations. The body is an object, not a bare array."""

    model_config = ConfigDict(extra="forbid")

    posts: list[ObservedXPost] = Field(
        min_length=X_SIGNAL_BATCH_MIN,
        max_length=X_SIGNAL_BATCH_MAX,
    )


class RejectedXPost(BaseModel):
    """An observation the intake did not store, with a stable reason code."""

    model_config = ConfigDict(extra="forbid")

    url: str
    reason: str


class XSignalsResponse(BaseModel):
    """Canonical URLs stored, and the observations the response rejects."""

    model_config = ConfigDict(extra="forbid")

    accepted: list[str]
    rejected: list[RejectedXPost]


class ScoutFailedBody(BaseModel):
    """Why the scout stopped. The text is delivered, not interpreted."""

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=TEXT_MIN_CHARS, max_length=SCOUT_REASON_MAX_CHARS)


class ScoutFailedResponse(BaseModel):
    """True when the owner was sent exactly one Telegram message."""

    model_config = ConfigDict(extra="forbid")

    delivered: bool


def _require_http_url(value: str) -> str:
    cleaned = strip_controls(value)
    if is_http_url(cleaned):
        return cleaned
    raise ValueError(SOURCE_URL_INVALID)
