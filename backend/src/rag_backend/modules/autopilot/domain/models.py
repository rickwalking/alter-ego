"""Autopilot aggregates and the run-state enum.

Private to the module. Column shapes follow
``docs/architecture/grokbot-autopilot.md`` §4. ``why_viral`` is included
because AE-0350's scope and the §5 scout output contract both require it
(the §4 column list omitted it).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from rag_backend.modules.autopilot.domain.carousel_defaults import DEFAULT_IMAGE_STYLE
from rag_backend.modules.autopilot.domain.notice_log import NoticeLog


class AutopilotRunState(StrEnum):
    """Legal states of an autopilot run (architecture §4)."""

    QUEUED = "queued"
    GENERATING = "generating"
    AWAITING_OWNER = "awaiting_owner"
    REWORKING = "reworking"
    ESCALATED = "escalated"
    FAILED = "failed"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    PUBLISH_FAILED = "publish_failed"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass(frozen=True, kw_only=True)
class TransitionPair:
    """The from/to pair a caller is asking the state machine to allow."""

    expected: AutopilotRunState
    new: AutopilotRunState


@dataclass(frozen=True, kw_only=True)
class TransitionCommand:
    """One compare-and-set request. One object keeps the call under 3 args."""

    run_id: UUID
    expected: AutopilotRunState
    new: AutopilotRunState
    reason: str

    def pair(self) -> TransitionPair:
        """The state pair the domain table judges, ignoring persistence."""
        return TransitionPair(expected=self.expected, new=self.new)


@dataclass(frozen=True, kw_only=True)
class TopicCandidate:
    """A scout topic stored for dedupe and for the run that consumes it."""

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
    # AE-0361: the scout's image preset and optional visual direction.
    image_style: str = DEFAULT_IMAGE_STYLE
    image_guidance: str | None = None


@dataclass(frozen=True, kw_only=True)
class AutopilotRun:
    """One autopilot run. ``carousel_project_id`` is null until generation."""

    run_id: UUID
    topic_candidate_id: UUID
    carousel_project_id: str | None
    state: AutopilotRunState
    state_reason: str | None
    # Publish attempts only. Start failures count in ``start_attempts``.
    publish_attempts: int
    telegram_message_ids: tuple[int, ...]
    ig_container_id: str | None
    ig_post_id: str | None
    ig_permalink: str | None
    # Set when the container id is first stored. ``updated_at`` moves on every
    # retry, so it cannot answer the 24h container-reuse rule.
    ig_container_created_at: datetime | None = None
    updated_at: datetime | None = None
    notice_log: NoticeLog = field(default_factory=NoticeLog)
    start_attempts: int = 0
    # Owner rework the webhook queued for the runner (phase + feedback text).
    rework_phase: str | None = None
    rework_feedback: str | None = None
    # Workflow lock version when the run was escalated. A different version
    # at final review means the owner changed the carousel in the web UI.
    escalated_version: int | None = None


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
