"""Request and response models for POST /api/autopilot/topics.

``extra=forbid`` rejects scout fields the contract does not name. Source
values must be http(s) URLs. Length limits match the ticket.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from rag_backend.domain.constants.content_mode import (
    CONTENT_MODE_NEWS_ANALYSIS,
    ERR_POV_FORMAT_UNKNOWN,
    POV_FORMATS,
    POV_SLIDE_COUNT_MAX,
    POV_SLIDE_COUNT_MIN,
)
from rag_backend.modules.autopilot.carousel_constants import (
    IMAGE_GUIDANCE_MAX_CHARS,
    IMAGE_STYLE_INPUT_MAX_CHARS,
)
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
from rag_backend.modules.autopilot.domain.carousel_defaults import DEFAULT_IMAGE_STYLE
from rag_backend.modules.autopilot.domain.topic_text import is_http_url, strip_controls
from rag_backend.modules.autopilot.pov_constants import (
    SCOUT_MODE_PATTERN,
    THESIS_DRAFT_MAX_CHARS,
)
from rag_backend.modules.autopilot.quote_constants import (
    QUOTE_FIELD_SCHEMA_MAX_CHARS,
    QUOTES_SCHEMA_MAX,
)

_QuoteText = Annotated[str, Field(max_length=QUOTE_FIELD_SCHEMA_MAX_CHARS)]


class QuoteProposal(BaseModel):
    """AE-0406 (spec §4): one verified quote of a post sent through x-signals.

    Unknown keys are a 422 for the batch. Every other rule (id pattern, name
    length, excerpt in the stored post, word limits) is a domain rule that
    rejects only this topic, with its reason code and ``field``.
    """

    model_config = ConfigDict(extra="forbid")

    id: _QuoteText
    url: _QuoteText
    handle: _QuoteText
    name: _QuoteText
    excerpt: _QuoteText
    lang_original: _QuoteText
    text_pt: _QuoteText
    text_en: _QuoteText


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
    # AE-0361: a plain short string here; the domain rejects an unsupported
    # preset for that topic only (``image_style_unsupported``), not the batch.
    image_style: str = Field(
        default=DEFAULT_IMAGE_STYLE,
        min_length=TEXT_MIN_CHARS,
        max_length=IMAGE_STYLE_INPUT_MAX_CHARS,
    )
    image_guidance: str | None = Field(
        default=None,
        min_length=TEXT_MIN_CHARS,
        max_length=IMAGE_GUIDANCE_MAX_CHARS,
    )
    # AE-0377 (scout v3): Radar IA when omitted; POV carries the draft thesis
    # the owner confirms on Telegram (the domain rejects a POV without one).
    mode: str = Field(default=CONTENT_MODE_NEWS_ANALYSIS, pattern=SCOUT_MODE_PATTERN)
    thesis_draft: str | None = Field(
        default=None,
        min_length=TEXT_MIN_CHARS,
        max_length=THESIS_DRAFT_MAX_CHARS,
    )

    # PR #106 review (scout v3): the POV format and slide count per topic.
    # Omitted = the autopilot default (opiniao, 9); ignored on Radar IA topics.
    pov_format: str | None = None
    slide_count: int | None = Field(
        default=None, ge=POV_SLIDE_COUNT_MIN, le=POV_SLIDE_COUNT_MAX
    )
    # AE-0406: up to 3 verified quotes on a ``pov_news`` topic (a 4th is a
    # ``quote_invalid`` rejection of that topic; the cap here is abuse only).
    quotes: list[QuoteProposal] = Field(
        default_factory=list, max_length=QUOTES_SCHEMA_MAX
    )

    @field_validator("pov_format")
    @classmethod
    def pov_format_is_known(cls, value: str | None) -> str | None:
        """Reject a batch whose POV format is not one of the four formats."""
        if value is None or value in POV_FORMATS:
            return value
        raise ValueError(ERR_POV_FORMAT_UNKNOWN.format(sorted(POV_FORMATS), value))

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
    """A proposal the intake did not queue, with a stable reason code.

    AE-0406: ``index`` (position in the request) is always present; ``field``
    only when one field caused the rejection (the route drops it otherwise).
    """

    model_config = ConfigDict(extra="forbid")

    index: int
    title: str
    reason: str
    field: str | None = None


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


# --- AE-0378: GET /api/instagram/insights (null metric = "n/d") ---


class InstagramPostInsightsItem(BaseModel):
    """One published post and its last metrics."""

    media_id: str
    carousel_project_id: str | None = None
    permalink: str | None = None
    topic: str | None = None
    views: int | None = None
    reach: int | None = None
    saved: int | None = None
    shares: int | None = None
    follows: int | None = None
    profile_visits: int | None = None
    total_interactions: int | None = None
    shares_per_100_views: float | None = None
    fetched_at: datetime | None = None
    stale: bool = Field(description="True when the metrics are older than 6 h.")


class InstagramInsightsResponse(BaseModel):
    """Rows (newest first) and the KPI ratios over the posts that report them."""

    items: list[InstagramPostInsightsItem]
    follows_total: int | None = None
    follows_per_post: float | None = None
    shares_per_100_views: float | None = None
    configured: bool = Field(description="False when no Graph account is set.")
