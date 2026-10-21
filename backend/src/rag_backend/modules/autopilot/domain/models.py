"""Autopilot aggregates and the run-state enum.

Private to the module. Column shapes follow
``docs/architecture/grokbot-autopilot.md`` §4. ``why_viral`` is included
because the scope and the §5 scout output contract both require it
(the §4 column list omitted it).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from rag_backend.domain.models.news_quote import NewsQuote
from rag_backend.modules.autopilot.domain.carousel_defaults import DEFAULT_IMAGE_STYLE
from rag_backend.modules.autopilot.domain.notice_log import NoticeLog


class AutopilotRunState(StrEnum):
    """Legal states of an autopilot run (architecture §4).

    ``SCHEDULED``: approved, waiting for the owner's publish time.
    ``AWAITING_THESIS``: a POV run waits for the owner to confirm the scout's
    thesis.
    """

    QUEUED = "queued"
    GENERATING = "generating"
    AWAITING_OWNER = "awaiting_owner"
    REWORKING = "reworking"
    ESCALATED = "escalated"
    FAILED = "failed"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    PUBLISH_FAILED = "publish_failed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    AWAITING_THESIS = "awaiting_thesis"


@dataclass(frozen=True, kw_only=True)
class TransitionPair:
    """The from/to pair a caller is asking the state machine to allow."""

    expected: AutopilotRunState
    new: AutopilotRunState


@dataclass(frozen=True, kw_only=True)
class TransitionCommand:
    """One compare-and-set request. One object keeps the call under 3 args.

    ``scheduled_at`` is the publish time stored when the run enters ``scheduled``;
    ``detail`` is extra escalation copy for the owner, carried on the state-changed
    event.
    """

    run_id: UUID
    expected: AutopilotRunState
    new: AutopilotRunState
    reason: str
    scheduled_at: datetime | None = None
    detail: str = ""

    def pair(self) -> TransitionPair:
        """The state pair the domain table judges, ignoring persistence."""
        return TransitionPair(expected=self.expected, new=self.new)


@dataclass(frozen=True, kw_only=True)
class ThesisConfirmCommand:
    """Store the owner's thesis and requeue the run in one CAS."""

    run_id: UUID
    thesis: str
    reason: str


@dataclass(frozen=True, kw_only=True)
class TopicCandidate:
    """A scout topic stored for dedupe and for the run that consumes it.

    ``image_style`` and ``image_guidance`` are the scout's image preset and optional
    visual direction. ``content_mode`` is Radar IA (None or ``news_analysis``) or
    POV with the scout's ``thesis_draft``. ``pov_format`` and ``slide_count`` are
    None for the default. ``quotes`` are the verified quotes of a ``pov_news`` topic
    (empty otherwise); ``cover_asset_id`` is the GrokBot cover the scout attached.
    """

    candidate_id: UUID
    title: str
    angle: str
    why_viral: str
    audience: str
    niche: str
    brief: str
    sources: tuple[str, ...]
    score: int
    signal_hash: str
    status: str
    image_style: str = DEFAULT_IMAGE_STYLE
    image_guidance: str | None = None
    content_mode: str | None = None
    thesis_draft: str | None = None
    pov_format: str | None = None
    slide_count: int | None = None
    quotes: tuple[NewsQuote, ...] = ()
    cover_asset_id: UUID | None = None


@dataclass(frozen=True, kw_only=True)
class AutopilotRun:
    """One autopilot run. ``carousel_project_id`` is null until generation.

    ``publish_attempts`` counts publish attempts only; start failures count in
    ``start_attempts``. ``ig_container_created_at`` is set when the container id is
    first stored: ``updated_at`` moves on every retry, so it cannot answer the 24h
    container-reuse rule. ``rework_phase`` and ``rework_feedback`` are the owner
    rework the webhook queued for the runner. ``escalated_version`` is the workflow
    lock version at escalation; a different version at final review means the owner
    changed the carousel in the web UI. ``pov_thesis`` is the thesis the owner
    confirmed (POV runs only) and ``cover_chosen`` turns True once the owner chose
    the GrokBot cover for slide 1. ``scheduled_at`` is when a ``scheduled`` run is
    due; it is kept after the due tick so the published notice can say how late it
    went out.
    """

    run_id: UUID
    topic_candidate_id: UUID
    carousel_project_id: str | None
    state: AutopilotRunState
    state_reason: str | None
    publish_attempts: int
    telegram_message_ids: tuple[int, ...]
    ig_container_id: str | None
    ig_post_id: str | None
    ig_permalink: str | None
    ig_container_created_at: datetime | None = None
    updated_at: datetime | None = None
    notice_log: NoticeLog = field(default_factory=NoticeLog)
    start_attempts: int = 0
    rework_phase: str | None = None
    rework_feedback: str | None = None
    escalated_version: int | None = None
    pov_thesis: str | None = None
    cover_chosen: bool = False
    scheduled_at: datetime | None = None


@dataclass(frozen=True, kw_only=True)
class IntegrationCredential:
    """Ciphertext stored for one provider. Callers decrypt at the edge."""

    provider: str
    encrypted_token: str
    expires_at: datetime | None
    refreshed_at: datetime | None


@dataclass(frozen=True, kw_only=True)
class TelegramUpdate:
    """A Telegram ``update_id`` kept so webhook retries are deduped."""

    update_id: int
    received_at: datetime
