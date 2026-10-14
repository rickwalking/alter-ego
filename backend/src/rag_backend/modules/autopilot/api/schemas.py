"""Request and response models for POST /api/autopilot/topics.

``extra=forbid`` rejects scout fields the contract does not name. Source
values must be http(s) URLs. Length limits match the ticket.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from rag_backend.modules.autopilot.constants import (
    ANGLE_MAX_CHARS,
    AUDIENCE_MAX_CHARS,
    BRIEF_MAX_CHARS,
    NICHE_MAX_CHARS,
    SCORE_MAX,
    SCORE_MIN,
    SOURCE_URL_INVALID,
    SOURCE_URL_MAX,
    SOURCE_URL_MIN,
    TEXT_MIN_CHARS,
    TITLE_MAX_CHARS,
    TOPIC_BATCH_MAX,
    TOPIC_BATCH_MIN,
    WHY_VIRAL_MAX_CHARS,
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
    sources: list[str] = Field(min_length=SOURCE_URL_MIN, max_length=SOURCE_URL_MAX)
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


def _require_http_url(value: str) -> str:
    cleaned = strip_controls(value)
    if is_http_url(cleaned):
        return cleaned
    raise ValueError(SOURCE_URL_INVALID)
