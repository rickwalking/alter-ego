"""The owner's Retry on a failed, blocked, escalated or rejected carousel. Pure.

``decide_retry`` reads the facts gathered under the carousel row lock and
answers what the Retry runs, or why it is refused:

- ``redrive``: the checkpoint is parked before a node (a phase that failed
  before its gate); the node re-runs from the checkpoint and stops at its gate.
- ``revise``: the gate is open but blocked (an approve blocker or an escalated
  autopilot run), the phase failed with its gate still open, or the system
  rejected the carousel at a gate; the phase is revised with a fixed,
  system-written feedback line that names the reason.
- ``reopen``: the system rejected the carousel at the final review; the review
  waits for the owner again. Nothing is re-generated.

Approved and published carousels, the final review of a live carousel and a
clean gate with no escalation are ``not_retryable``. A queue dead letter is the
reprocess action's job (``use_reprocess``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_MUTATION_IN_PROGRESS,
    CONFLICT_CODE_REVISION_CAP_EXCEEDED,
    CONFLICT_CODE_RUN_IN_PROGRESS,
    CONFLICT_CODE_VERSION_CONFLICT,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_FINAL_REVIEW,
    PHASE_PUBLISHED,
    PHASE_STATUS_APPROVED,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_REJECTED,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.constants.workflow_validation import ERR_NOT_ASSIGNED_REVIEWER
from rag_backend.modules.generation_queue.constants import (
    AUTOPILOT_DEAD_LETTER_PREFIX,
    AUTOPILOT_STATE_ESCALATED,
    DRIVEN_AUTOPILOT_STATES,
    RETRY_REASON_GATE_BLOCKED,
    RETRY_REASON_PHASE_FAILED,
    RETRY_REASON_REJECTED,
)


class RetryKind(StrEnum):
    """What an accepted Retry runs."""

    REDRIVE = "redrive"
    REVISE = "revise"
    REOPEN = "reopen"


class RetryRefusal(StrEnum):
    """Stable refusal codes; the ones that already exist keep their values."""

    NOT_FOUND = "not_found"
    NOT_OWNER = "not_owner"
    NOT_ASSIGNED_REVIEWER = ERR_NOT_ASSIGNED_REVIEWER
    NOT_RETRYABLE = "not_retryable"
    RUN_IN_PROGRESS = CONFLICT_CODE_RUN_IN_PROGRESS
    MUTATION_IN_PROGRESS = CONFLICT_CODE_MUTATION_IN_PROGRESS
    USE_REPROCESS = "use_reprocess"
    AUTOPILOT_ACTIVE = "autopilot_active"
    NO_CHECKPOINT = "no_checkpoint"
    VERSION_CONFLICT = CONFLICT_CODE_VERSION_CONFLICT
    REVISION_CAP_EXCEEDED = CONFLICT_CODE_REVISION_CAP_EXCEEDED
    CONCURRENT_UPDATE = "concurrent_update"


class RetrySurface(StrEnum):
    """Where the owner pressed Retry."""

    WEB = "web"
    TELEGRAM = "telegram"


@dataclass(frozen=True, kw_only=True)
class OwnerRetryCommand:
    """One Retry; the website sends ``expected_version``, Telegram does not."""

    project_id: str
    actor_id: str
    surface: RetrySurface
    expected_version: int | None = None


@dataclass(frozen=True, kw_only=True)
class CarouselRetryState:
    """The carousel row as read under its lock."""

    owner_id: str | None
    assigned_reviewer_id: str | None
    topic: str
    phase: str
    phase_status: str
    status: str
    workflow_status: str
    lock_version: int


@dataclass(frozen=True, kw_only=True)
class CheckpointFacts:
    """The LangGraph checkpoint: present, parked, its approve blocker and score."""

    present: bool
    parked: bool = False
    blocker: str | None = None
    persona_score: float | None = None


@dataclass(frozen=True, kw_only=True)
class AutopilotFacts:
    """The carousel's autopilot run, when it has one."""

    run_id: UUID
    state: str
    reason: str | None = None


@dataclass(frozen=True, kw_only=True)
class QueueFacts:
    """The generation queue and the artifact lock around the carousel."""

    active_run: bool = False
    held_run: bool = False
    mutation_locked: bool = False


@dataclass(frozen=True, kw_only=True)
class RetryFacts:
    """Everything ``decide_retry`` reads."""

    actor_id: str
    carousel: CarouselRetryState
    checkpoint: CheckpointFacts
    queue: QueueFacts
    autopilot: AutopilotFacts | None = None


@dataclass(frozen=True, kw_only=True)
class RetryDecision:
    """One kind with the reason the feedback line names, or one refusal."""

    kind: RetryKind | None = None
    refusal: RetryRefusal | None = None
    reason: str = ""


_Guard = Callable[[RetryFacts], RetryRefusal | None]
_FINISHED_PHASE_STATUSES = frozenset({PHASE_STATUS_APPROVED})


def decide_retry(facts: RetryFacts) -> RetryDecision:
    """The first refusal that applies, else the kind for the carousel's state."""
    for guard in _GUARDS:
        refusal = guard(facts)
        if refusal is not None:
            return RetryDecision(refusal=refusal)
    decide = _BY_PHASE_STATUS.get(facts.carousel.phase_status, _other)
    return decide(facts)


def escalated_run(facts: RetryFacts) -> AutopilotFacts | None:
    """The autopilot run a Retry moves back to generating, when escalated."""
    run = facts.autopilot
    if run is None or run.state != AUTOPILOT_STATE_ESCALATED:
        return None
    return run


def _not_owner(facts: RetryFacts) -> RetryRefusal | None:
    if facts.carousel.owner_id == facts.actor_id:
        return None
    return RetryRefusal.NOT_OWNER


def _not_reviewer(facts: RetryFacts) -> RetryRefusal | None:
    reviewer = facts.carousel.assigned_reviewer_id
    if not reviewer or reviewer == facts.actor_id:
        return None
    return RetryRefusal.NOT_ASSIGNED_REVIEWER


def _running(facts: RetryFacts) -> RetryRefusal | None:
    if facts.carousel.phase_status == PHASE_STATUS_IN_PROGRESS:
        return RetryRefusal.RUN_IN_PROGRESS
    if facts.queue.active_run:
        return RetryRefusal.RUN_IN_PROGRESS
    return None


def _mutating(facts: RetryFacts) -> RetryRefusal | None:
    if facts.queue.mutation_locked:
        return RetryRefusal.MUTATION_IN_PROGRESS
    return None


def _autopilot_driving(facts: RetryFacts) -> RetryRefusal | None:
    run = facts.autopilot
    if run is not None and run.state in DRIVEN_AUTOPILOT_STATES:
        return RetryRefusal.AUTOPILOT_ACTIVE
    return None


def _dead_letter(facts: RetryFacts) -> RetryRefusal | None:
    if facts.queue.held_run:
        return RetryRefusal.USE_REPROCESS
    run = escalated_run(facts)
    if run is not None and (run.reason or "").startswith(AUTOPILOT_DEAD_LETTER_PREFIX):
        return RetryRefusal.USE_REPROCESS
    return None


def _finished(facts: RetryFacts) -> RetryRefusal | None:
    carousel = facts.carousel
    if carousel.phase == PHASE_PUBLISHED:
        return RetryRefusal.NOT_RETRYABLE
    if carousel.workflow_status == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH:
        return RetryRefusal.NOT_RETRYABLE
    if carousel.phase_status in _FINISHED_PHASE_STATUSES:
        return RetryRefusal.NOT_RETRYABLE
    return None


def _no_checkpoint(facts: RetryFacts) -> RetryRefusal | None:
    if facts.checkpoint.present:
        return None
    return RetryRefusal.NO_CHECKPOINT


_GUARDS: tuple[_Guard, ...] = (
    _not_owner,
    _not_reviewer,
    _running,
    _mutating,
    _autopilot_driving,
    _dead_letter,
    _finished,
    _no_checkpoint,
)


def _rejected(facts: RetryFacts) -> RetryDecision:
    """A system reject: reopen the final review, else re-run the phase."""
    if facts.carousel.phase == PHASE_FINAL_REVIEW:
        return RetryDecision(kind=RetryKind.REOPEN, reason=RETRY_REASON_REJECTED)
    return _rerun(facts, RETRY_REASON_REJECTED)


def _failed(facts: RetryFacts) -> RetryDecision:
    """A failed phase: re-drive the parked node, else revise the open gate."""
    if facts.checkpoint.parked:
        return _rerun(facts, RETRY_REASON_PHASE_FAILED)
    if facts.carousel.phase == PHASE_FINAL_REVIEW:
        return RetryDecision(refusal=RetryRefusal.NOT_RETRYABLE)
    return _rerun(facts, RETRY_REASON_PHASE_FAILED)


def _awaiting(facts: RetryFacts) -> RetryDecision:
    """An open gate is retried only when it is blocked or its run escalated."""
    if facts.checkpoint.parked:
        return _rerun(facts, RETRY_REASON_GATE_BLOCKED)
    if facts.carousel.phase == PHASE_FINAL_REVIEW:
        return RetryDecision(refusal=RetryRefusal.NOT_RETRYABLE)
    reason = _block_reason(facts)
    if not reason:
        return RetryDecision(refusal=RetryRefusal.NOT_RETRYABLE)
    return RetryDecision(kind=RetryKind.REVISE, reason=reason)


def _other(facts: RetryFacts) -> RetryDecision:
    """Any other state is retried only when a node is parked."""
    if facts.checkpoint.parked:
        return _rerun(facts, RETRY_REASON_GATE_BLOCKED)
    return RetryDecision(refusal=RetryRefusal.NOT_RETRYABLE)


def _rerun(facts: RetryFacts, fallback: str) -> RetryDecision:
    """Re-drive a parked node, or revise the gate naming the best reason."""
    reason = _block_reason(facts) or fallback
    if facts.checkpoint.parked:
        return RetryDecision(kind=RetryKind.REDRIVE, reason=reason)
    return RetryDecision(kind=RetryKind.REVISE, reason=reason)


def _block_reason(facts: RetryFacts) -> str:
    """The escalation reason, else the engine's approve blocker, else empty."""
    run = escalated_run(facts)
    if run is not None and run.reason:
        return run.reason
    return facts.checkpoint.blocker or ""


_BY_PHASE_STATUS: dict[str, Callable[[RetryFacts], RetryDecision]] = {
    PHASE_STATUS_REJECTED: _rejected,
    PHASE_STATUS_FAILED: _failed,
    PHASE_STATUS_AWAITING_HUMAN: _awaiting,
}


__all__ = [
    "AutopilotFacts",
    "CarouselRetryState",
    "CheckpointFacts",
    "OwnerRetryCommand",
    "QueueFacts",
    "RetryDecision",
    "RetryFacts",
    "RetryKind",
    "RetryRefusal",
    "RetrySurface",
    "decide_retry",
    "escalated_run",
]
