"""Pure stuck-only classification for manual carousel recovery."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.modules.generation_queue.constants import (
    AUTOPILOT_OWNER_WAIT_STATES,
    DRIVEN_AUTOPILOT_STATES,
)
from rag_backend.modules.generation_queue.domain.manual_recovery import (
    RecoveryDecision,
    RecoveryPolicy,
    RecoverySnapshot,
    RefusalCode,
    StuckKind,
    recovery_lock_keys,
)
from rag_backend.modules.generation_queue.domain.models import (
    GenerationKind,
    GenerationRun,
    GenerationStatus,
)


def classify_recovery(
    snapshot: RecoverySnapshot, now: datetime, policy: RecoveryPolicy
) -> RecoveryDecision:
    """Classify exactly one recoverable kind or a stable refusal."""
    version = _version_refusal(snapshot)
    if version is not None:
        return RecoveryDecision(refusal=version)
    if _owner_waiting(snapshot):
        return RecoveryDecision(refusal=RefusalCode.OWNER_WAITING)
    if snapshot.run is None:
        return _without_run(snapshot, now, policy)
    return _with_run(snapshot, now, policy)


def _version_refusal(snapshot: RecoverySnapshot) -> RefusalCode | None:
    expected = snapshot.command.expected_version
    project = snapshot.project
    if expected is None or project is None or project.lock_version == expected:
        return None
    return RefusalCode.STALE_VERSION


def _owner_waiting(snapshot: RecoverySnapshot) -> bool:
    if snapshot.autopilot_state in AUTOPILOT_OWNER_WAIT_STATES:
        return True
    return (
        snapshot.project is not None
        and snapshot.project.phase_status == PHASE_STATUS_AWAITING_HUMAN
    )


def _without_run(
    snapshot: RecoverySnapshot, now: datetime, policy: RecoveryPolicy
) -> RecoveryDecision:
    if snapshot.project is None:
        return RecoveryDecision(refusal=RefusalCode.PROJECTLESS_UNSTAGED)
    return _orphan(snapshot, now, policy)


def _with_run(
    snapshot: RecoverySnapshot, now: datetime, policy: RecoveryPolicy
) -> RecoveryDecision:
    run = snapshot.run
    if run is None or snapshot.latest_run_id != run.id:
        return RecoveryDecision(refusal=RefusalCode.UNSUPPORTED)
    if snapshot.active_run_id is not None and snapshot.active_run_id != run.id:
        return RecoveryDecision(refusal=RefusalCode.NORMAL_QUEUED)
    if run.status is GenerationStatus.DEAD_LETTER:
        return _dead(run, autopilot_dead=snapshot.autopilot_dead)
    if run.status is GenerationStatus.RETRY_WAIT:
        return _retry(run)
    return _active_or_orphan(snapshot, now, policy)


def _active_or_orphan(
    snapshot: RecoverySnapshot, now: datetime, policy: RecoveryPolicy
) -> RecoveryDecision:
    run = snapshot.run
    if run is not None and run.status is GenerationStatus.QUEUED:
        return RecoveryDecision(refusal=RefusalCode.NORMAL_QUEUED)
    if run is not None and run.status is GenerationStatus.RUNNING:
        return _running(snapshot, now, policy)
    return _orphan(snapshot, now, policy)


def _dead(run: GenerationRun, *, autopilot_dead: bool | None) -> RecoveryDecision:
    if autopilot_dead is False or _malformed_autopilot(run):
        return RecoveryDecision(refusal=RefusalCode.UNSUPPORTED)
    return RecoveryDecision(stuck=StuckKind.DEAD_LETTER)


def _retry(run: GenerationRun) -> RecoveryDecision:
    if _malformed_autopilot(run):
        return RecoveryDecision(refusal=RefusalCode.UNSUPPORTED)
    return RecoveryDecision(stuck=StuckKind.RETRY_WAIT)


def _malformed_autopilot(run: GenerationRun) -> bool:
    return run.kind is GenerationKind.AUTOPILOT_DRIVE and run.autopilot_run_id is None


def _running(
    snapshot: RecoverySnapshot, now: datetime, policy: RecoveryPolicy
) -> RecoveryDecision:
    project = snapshot.project
    if project is None or project.heartbeat_at is None:
        return RecoveryDecision(refusal=RefusalCode.NULL_HEARTBEAT)
    age = _aware(now) - _aware(project.heartbeat_at)
    if age <= timedelta(seconds=policy.heartbeat_stale_seconds):
        return RecoveryDecision(refusal=RefusalCode.FRESH_RUNNING)
    if not recovery_lock_keys(snapshot):
        return RecoveryDecision(refusal=RefusalCode.UNSUPPORTED)
    return RecoveryDecision(stuck=StuckKind.STALE_RUNNING)


def _orphan(
    snapshot: RecoverySnapshot, now: datetime, policy: RecoveryPolicy
) -> RecoveryDecision:
    if snapshot.active_run_id is not None:
        return RecoveryDecision(refusal=RefusalCode.NORMAL_QUEUED)
    if (
        snapshot.autopilot_state is not None
        and snapshot.autopilot_state not in DRIVEN_AUTOPILOT_STATES
    ):
        return RecoveryDecision(refusal=RefusalCode.UNSUPPORTED)
    project = snapshot.project
    if project is None or project.phase_status != PHASE_STATUS_IN_PROGRESS:
        return RecoveryDecision(refusal=RefusalCode.UNSUPPORTED)
    age = _aware(now) - _aware(project.updated_at)
    if age <= timedelta(seconds=policy.dispatcher_grace_seconds):
        return RecoveryDecision(refusal=RefusalCode.DISPATCHER_GRACE)
    return RecoveryDecision(stuck=StuckKind.ORPHAN)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = ["classify_recovery"]
