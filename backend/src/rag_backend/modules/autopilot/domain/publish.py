"""Pure Instagram publish decisions. No I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from rag_backend.domain.constants.carousel import CAROUSEL_STATUS_COMPLETED
from rag_backend.domain.constants.carousel_workflow import (
    ERR_CAROUSEL_NOT_COMPLETED,
    ERR_WORKFLOW_NOT_APPROVED_FOR_PUBLISH,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.constants.instagram_publish import (
    ERR_INSTAGRAM_IMAGE_COUNT_INVALID,
    MAX_INSTAGRAM_CAROUSEL_ITEMS,
    MIN_INSTAGRAM_CAROUSEL_ITEMS,
)
from rag_backend.modules.autopilot.constants import (
    CONTAINER_REUSE_HOURS,
    PUBLISH_BACKOFF_SECONDS,
    PUBLISH_MAX_ATTEMPTS,
    REASON_CAROUSEL_MISSING,
    REASON_CAROUSEL_NOT_PUBLIC,
    REASON_PUBLIC_BASE_URL_MISSING,
)
from rag_backend.modules.autopilot.domain.models import AutopilotRunState


class PublishAction:
    """What the next Graph call should do for one run."""

    ALREADY_POSTED = "already_posted"
    RESUME_CONTAINER = "resume_container"
    CREATE_CONTAINER = "create_container"


@dataclass(frozen=True, kw_only=True)
class PublishFacts:
    """The fields the idempotency branch reads. One object keeps calls small."""

    ig_post_id: str | None
    ig_container_id: str | None
    container_created_at: datetime | None
    now: datetime


@dataclass(frozen=True, kw_only=True)
class DueFacts:
    """Whether a publishing run may be picked on this tick."""

    attempts: int
    updated_at: datetime | None
    now: datetime


@dataclass(frozen=True, kw_only=True)
class PublishGate:
    """Local pre-checks that run before any Graph call."""

    project_found: bool
    base_url_configured: bool
    workflow_status: str
    status: str
    is_public: bool
    image_count: int


@dataclass(frozen=True, kw_only=True)
class CarouselMedia:
    """Caption and public slide URLs sent to Graph."""

    caption: str
    image_urls: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class RunListQuery:
    """Bound for ``list_by_state``."""

    state: AutopilotRunState
    limit: int


@dataclass(frozen=True, kw_only=True)
class SaveContainerCommand:
    """Persist the parent container before ``media_publish``."""

    run_id: UUID
    container_id: str
    created_at: datetime


@dataclass(frozen=True, kw_only=True)
class SavePostCommand:
    """Persist the media id and, when known, the permalink."""

    run_id: UUID
    ig_post_id: str
    ig_permalink: str | None


@dataclass(frozen=True, kw_only=True)
class PublishAttemptCommand:
    """Record one transient failure without leaving ``publishing``."""

    run_id: UUID
    attempts: int
    reason: str
    at: datetime


@dataclass(frozen=True, kw_only=True)
class AtomicPublishResult:
    """Outcome of a publisher that cannot pause between container and publish."""

    status: str
    post_id: str | None
    error_message: str | None


@dataclass(frozen=True, kw_only=True)
class ManualPublishCommand:
    """One owner-triggered publish. URLs are already built by the route."""

    project_id: str
    caption: str
    image_urls: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class ManualPublishOutcome:
    """Mapped onto the existing Instagram publish HTTP body."""

    status: str
    ig_post_id: str | None
    error_message: str | None


@dataclass(frozen=True, kw_only=True)
class PublishNotice:
    """What the owner is told. AE-0355 renders this on Telegram."""

    run_id: UUID
    outcome: str
    permalink: str | None
    error_code: str | None
    offer_retry: bool


def choose_publish_action(facts: PublishFacts) -> str:
    """Return the idempotency branch for this run."""
    if facts.ig_post_id:
        return PublishAction.ALREADY_POSTED
    if facts.ig_container_id and _container_is_fresh(facts):
        return PublishAction.RESUME_CONTAINER
    return PublishAction.CREATE_CONTAINER


def is_publish_due(facts: DueFacts) -> bool:
    """True when backoff has elapsed, or the run has never failed."""
    if facts.attempts >= PUBLISH_MAX_ATTEMPTS:
        return True
    if facts.attempts <= 0 or facts.updated_at is None:
        return True
    wait = _backoff_seconds(facts.attempts)
    return facts.now >= facts.updated_at + timedelta(seconds=wait)


def gate_reason(gate: PublishGate) -> str | None:
    """Permanent pre-check failure, or None when the carousel may be posted."""
    for reason in (
        _project_reason(gate),
        _workflow_reason(gate),
        _media_reason(gate),
    ):
        if reason is not None:
            return reason
    return None


def _project_reason(gate: PublishGate) -> str | None:
    if not gate.project_found:
        return REASON_CAROUSEL_MISSING
    if not gate.base_url_configured:
        return REASON_PUBLIC_BASE_URL_MISSING
    return None


def _workflow_reason(gate: PublishGate) -> str | None:
    if gate.workflow_status != WORKFLOW_STATUS_APPROVED_FOR_PUBLISH:
        return ERR_WORKFLOW_NOT_APPROVED_FOR_PUBLISH
    if gate.status != CAROUSEL_STATUS_COMPLETED:
        return ERR_CAROUSEL_NOT_COMPLETED
    if not gate.is_public:
        return REASON_CAROUSEL_NOT_PUBLIC
    return None


def _media_reason(gate: PublishGate) -> str | None:
    too_few = gate.image_count < MIN_INSTAGRAM_CAROUSEL_ITEMS
    too_many = gate.image_count > MAX_INSTAGRAM_CAROUSEL_ITEMS
    if too_few or too_many:
        return ERR_INSTAGRAM_IMAGE_COUNT_INVALID
    return None


def _container_is_fresh(facts: PublishFacts) -> bool:
    created = facts.container_created_at
    if created is None:
        return False
    return facts.now - created < timedelta(hours=CONTAINER_REUSE_HOURS)


def _backoff_seconds(attempts: int) -> int:
    index = min(attempts, len(PUBLISH_BACKOFF_SECONDS)) - 1
    return PUBLISH_BACKOFF_SECONDS[index]
