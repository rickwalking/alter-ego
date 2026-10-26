"""Typed commands, snapshots and results for manual carousel recovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from rag_backend.modules.generation_queue.constants import (
    MANUAL_ORIGIN_REPROCESS,
    MANUAL_REPROCESS_PRIORITY,
    PAYLOAD_MANUAL_ACTOR_ID,
    PAYLOAD_MANUAL_ORIGIN,
    PAYLOAD_MANUAL_PRIORITY,
    PAYLOAD_MANUAL_REQUEST_ID,
    PAYLOAD_MANUAL_REQUESTED_AT,
    PAYLOAD_MANUAL_STUCK_KIND,
)
from rag_backend.modules.generation_queue.domain.drive_lock_keys import (
    autopilot_lock_keys,
    project_key,
)
from rag_backend.modules.generation_queue.domain.models import (
    ATTEMPT_ID_KEY,
    GenerationKind,
    GenerationRun,
)


class StuckKind(StrEnum):
    """The only four recoverable stuck states."""

    DEAD_LETTER = "dead_letter"
    RETRY_WAIT = "retry_wait"
    STALE_RUNNING = "stale_running"
    ORPHAN = "orphan"


class RefusalCode(StrEnum):
    """Stable reasons returned as HTTP 409 details."""

    STALE_VERSION = "stale_expected_version"
    OWNER_WAITING = "owner_waiting"
    NORMAL_QUEUED = "normal_queued"
    DISPATCHER_GRACE = "dispatcher_grace"
    FRESH_RUNNING = "fresh_running"
    NULL_HEARTBEAT = "null_heartbeat"
    DRIVE_ACTIVE = "drive_active"
    UNSUPPORTED = "unsupported"
    PROJECTLESS_UNSTAGED = "projectless_unstaged"
    CONCURRENT_UPDATE = "concurrent_update"


class RecoveryOutcome(StrEnum):
    """The public result of one reprocess request."""

    QUEUED = "queued"
    EXISTING = "existing"
    REFUSED = "refused"
    NOT_FOUND = "not_found"


class WriteStatus(StrEnum):
    """The store's atomic write verdict."""

    APPLIED = "applied"
    EXISTING = "existing"
    STALE_VERSION = "stale_version"
    CONFLICT = "conflict"


@dataclass(frozen=True, kw_only=True)
class ManualReprocessCommand:
    """One actor's request against a project or an existing generation run."""

    project_id: str | None
    run_id: UUID | None
    actor_id: str
    expected_version: int | None = None
    request_id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, kw_only=True)
class ProjectRecoveryState:
    """The project fields used for classification and optimistic locking."""

    id: str
    title: str
    phase_status: str
    lock_version: int
    heartbeat_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True, kw_only=True)
class RecoveryPolicy:
    """Configured reaper and dispatcher time windows."""

    heartbeat_stale_seconds: int
    dispatcher_grace_seconds: int


@dataclass(frozen=True, kw_only=True)
class RecoverySnapshot:
    """A fresh target state read without any workflow execution."""

    command: ManualReprocessCommand
    run: GenerationRun | None
    project: ProjectRecoveryState | None
    latest_run_id: UUID | None = None
    active_run_id: UUID | None = None
    autopilot_dead: bool | None = None
    autopilot_run_id: str | None = None
    autopilot_state: str | None = None
    missing: bool = False


@dataclass(frozen=True, kw_only=True)
class RecoveryDecision:
    """One stuck kind or one stable refusal."""

    stuck: StuckKind | None = None
    refusal: RefusalCode | None = None


@dataclass(frozen=True, kw_only=True)
class RecoveryMutation:
    """The fenced values for one accepted atomic write."""

    snapshot: RecoverySnapshot
    stuck: StuckKind
    attempt_id: UUID
    requested_at: datetime


@dataclass(frozen=True, kw_only=True)
class RecoveryWrite:
    """A run linked by the atomic write, or a refusal verdict."""

    status: WriteStatus
    run: GenerationRun | None = None
    lock_version: int | None = None


@dataclass(frozen=True, kw_only=True)
class RecoveryResult:
    """The service result mapped to HTTP by the API."""

    outcome: RecoveryOutcome
    run: GenerationRun | None = None
    stuck_kind: StuckKind | None = None
    refusal: RefusalCode | None = None
    lock_version: int | None = None
    worker_notified: bool = False
    position: int | None = None
    eta_seconds: int | None = None


@dataclass(frozen=True, kw_only=True)
class RecoveryCapability:
    """Workspace capability and safe current-run progress."""

    can_reprocess: bool
    run: GenerationRun | None
    lock_version: int | None
    stuck_kind: StuckKind | None = None
    refusal: RefusalCode | None = None
    position: int | None = None
    eta_seconds: int | None = None


@dataclass(frozen=True, kw_only=True)
class AuditCommand:
    """The complete allowlist for a reprocess audit event."""

    actor_id: str
    project_id: str | None
    run_id: UUID
    stuck_kind: StuckKind
    lock_version: int | None


@dataclass(frozen=True, kw_only=True)
class MaintenanceNotice:
    """The future dispatch-only maintenance payload."""

    run_id: UUID


def is_manual_run(run: GenerationRun) -> bool:
    """Whether the active run was created or taken over by manual recovery."""
    return run.payload.get(PAYLOAD_MANUAL_ORIGIN) == MANUAL_ORIGIN_REPROCESS


def manual_stuck_kind(run: GenerationRun) -> StuckKind | None:
    """Read the safe stuck kind from a compatible manual run."""
    value = run.payload.get(PAYLOAD_MANUAL_STUCK_KIND)
    try:
        return StuckKind(str(value))
    except ValueError:
        return None


def manual_payload(mutation: RecoveryMutation) -> dict[str, object]:
    """Metadata shared by every accepted manual takeover."""
    command = mutation.snapshot.command
    return {
        ATTEMPT_ID_KEY: str(mutation.attempt_id),
        PAYLOAD_MANUAL_ORIGIN: MANUAL_ORIGIN_REPROCESS,
        PAYLOAD_MANUAL_REQUEST_ID: str(command.request_id),
        PAYLOAD_MANUAL_ACTOR_ID: command.actor_id,
        PAYLOAD_MANUAL_STUCK_KIND: mutation.stuck.value,
        PAYLOAD_MANUAL_REQUESTED_AT: mutation.requested_at.isoformat(),
        PAYLOAD_MANUAL_PRIORITY: MANUAL_REPROCESS_PRIORITY,
    }


def recovery_lock_keys(snapshot: RecoverySnapshot) -> list[str]:
    """Build exactly the lock set the executor would hold for this target."""
    run = snapshot.run
    project_id = snapshot.project.id if snapshot.project is not None else None
    if run is not None and run.kind is GenerationKind.AUTOPILOT_DRIVE:
        if run.autopilot_run_id is None:
            return []
        return autopilot_lock_keys(run.autopilot_run_id, project_id)
    if run is None and snapshot.autopilot_run_id is not None and project_id is not None:
        return autopilot_lock_keys(snapshot.autopilot_run_id, project_id)
    if project_id is None:
        return []
    return [project_key(project_id)]


__all__ = [
    "AuditCommand",
    "MaintenanceNotice",
    "ManualReprocessCommand",
    "ProjectRecoveryState",
    "RecoveryCapability",
    "RecoveryDecision",
    "RecoveryMutation",
    "RecoveryOutcome",
    "RecoveryPolicy",
    "RecoveryResult",
    "RecoverySnapshot",
    "RecoveryWrite",
    "RefusalCode",
    "StuckKind",
    "WriteStatus",
    "is_manual_run",
    "manual_payload",
    "manual_stuck_kind",
    "recovery_lock_keys",
]
