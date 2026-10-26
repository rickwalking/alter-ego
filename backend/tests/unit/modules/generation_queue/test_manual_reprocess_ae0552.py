"""Manual recovery service transaction, lock and notification behavior."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

from rag_backend.domain.constants.carousel_workflow import PHASE_STATUS_IN_PROGRESS
from rag_backend.modules.generation_queue.application.manual_reprocess import (
    ManualRecoveryDependencies,
    ManualRecoveryService,
)
from rag_backend.modules.generation_queue.domain.manual_recovery import (
    ManualReprocessCommand,
    ProjectRecoveryState,
    RecoveryOutcome,
    RecoveryPolicy,
    RecoverySnapshot,
    RecoveryWrite,
    RefusalCode,
    StuckKind,
    WriteStatus,
    manual_stuck_kind,
)
from rag_backend.modules.generation_queue.domain.models import GenerationStatus
from tests.unit.modules.generation_queue.manual_recovery_fakes import (
    FakeDriveLock,
    FakeMaintenanceNotifier,
    FakeManualStore,
    FakeRecoveryAudit,
)
from tests.unit.modules.generation_queue.queue_fakes import (
    NOW,
    FixedClock,
    make_run,
    resume_run,
)

POLICY = RecoveryPolicy(heartbeat_stale_seconds=180, dispatcher_grace_seconds=600)


def _project() -> ProjectRecoveryState:
    return ProjectRecoveryState(
        id="p1",
        title="Safe title",
        phase_status=PHASE_STATUS_IN_PROGRESS,
        lock_version=4,
        heartbeat_at=NOW - timedelta(seconds=181),
        updated_at=NOW - timedelta(seconds=601),
    )


def _command(**overrides: object) -> ManualReprocessCommand:
    command = ManualReprocessCommand(
        project_id="p1", run_id=None, actor_id="actor", expected_version=4
    )
    return replace(command, **overrides)


def _snapshot(kind: StuckKind) -> RecoverySnapshot:
    if kind is StuckKind.ORPHAN:
        return RecoverySnapshot(
            command=_command(), run=None, project=_project(), active_run_id=None
        )
    statuses = {
        StuckKind.DEAD_LETTER: GenerationStatus.DEAD_LETTER,
        StuckKind.RETRY_WAIT: GenerationStatus.RETRY_WAIT,
        StuckKind.STALE_RUNNING: GenerationStatus.RUNNING,
    }
    run = make_run(status=statuses[kind])
    return RecoverySnapshot(
        command=_command(),
        run=run,
        project=_project(),
        latest_run_id=run.id,
        active_run_id=run.id if run.status is GenerationStatus.RUNNING else None,
    )


def _write(snapshot: RecoverySnapshot) -> RecoveryWrite:
    run = snapshot.run or resume_run(status=GenerationStatus.QUEUED)
    return RecoveryWrite(
        status=WriteStatus.APPLIED,
        run=replace(run, status=GenerationStatus.QUEUED),
        lock_version=5,
    )


def _service(
    kind: StuckKind,
) -> tuple[
    ManualRecoveryService,
    FakeManualStore,
    FakeRecoveryAudit,
    FakeMaintenanceNotifier,
    FakeDriveLock,
]:
    events: list[str] = []
    snapshot = _snapshot(kind)
    store = FakeManualStore(snapshot=snapshot, write=_write(snapshot), events=events)
    audit = FakeRecoveryAudit(events=events)
    notifier = FakeMaintenanceNotifier(events=events)
    lock = FakeDriveLock()
    service = ManualRecoveryService(
        ManualRecoveryDependencies(
            store=store,
            audit=audit,
            lock=lock,
            notifier=notifier,
            clock=FixedClock(),
            policy=POLICY,
        )
    )
    return service, store, audit, notifier, lock


async def test_accept_audits_commits_then_notifies() -> None:
    """Scenario: Retry wait becomes eligible immediately and kicks maintenance."""
    service, store, audit, notifier, _ = _service(StuckKind.RETRY_WAIT)
    result = await service.reprocess(_command())
    assert result.outcome is RecoveryOutcome.QUEUED
    assert result.worker_notified is True
    assert result.lock_version == 5
    assert store.events == ["audit", "commit", "notify"]
    assert len(audit.commands) == 1
    assert len(notifier.notices) == 1


async def test_notifier_failure_is_honest_after_durable_commit() -> None:
    """Scenario: A control-enqueue failure leaves the accepted run durable."""
    service, store, _, notifier, _ = _service(StuckKind.DEAD_LETTER)
    notifier.error = RuntimeError("queue unavailable")
    result = await service.reprocess(_command())
    assert result.outcome is RecoveryOutcome.QUEUED
    assert result.worker_notified is False
    assert store.events == ["audit", "commit", "notify"]


async def test_existing_response_precedes_version_cas_and_audit() -> None:
    """Scenario: A sequential double click returns the existing manual run."""
    service, store, audit, notifier, _ = _service(StuckKind.RETRY_WAIT)
    existing = replace(store.write.run, payload={"manual_origin": "carousel_reprocess"})
    store.existing = existing
    command = _command(expected_version=3)
    result = await service.reprocess(command)
    assert result.outcome is RecoveryOutcome.EXISTING
    assert result.run == existing
    assert result.stuck_kind is manual_stuck_kind(existing)
    assert store.apply_calls == 0
    assert audit.commands == []
    assert store.events == ["commit", "notify"]
    assert len(notifier.notices) == 1


async def test_stale_expected_version_does_no_work() -> None:
    """Scenario: A stale expected version is a stable 409 refusal."""
    service, store, audit, notifier, _ = _service(StuckKind.DEAD_LETTER)
    result = await service.reprocess(_command(expected_version=3))
    assert result.outcome is RecoveryOutcome.REFUSED
    assert result.refusal is RefusalCode.STALE_VERSION
    assert store.apply_calls == 0
    assert audit.commands == []
    assert notifier.notices == []


async def test_stale_takeover_uses_complete_lock_set() -> None:
    """Scenario: A stale running row is taken over with both executor keys."""
    service, _, _, _, lock = _service(StuckKind.STALE_RUNNING)
    result = await service.reprocess(_command())
    assert result.outcome is RecoveryOutcome.QUEUED
    assert lock.held == [["autopilot:r1", "project:p1"]]


async def test_busy_lock_is_a_refusal_without_audit() -> None:
    """Scenario: A busy executor lock refuses takeover without new work."""
    service, store, audit, notifier, lock = _service(StuckKind.STALE_RUNNING)
    lock.busy = True
    result = await service.reprocess(_command())
    assert result.refusal is RefusalCode.DRIVE_ACTIVE
    assert store.apply_calls == 0
    assert audit.commands == []
    assert notifier.notices == []


async def test_state_is_reread_after_lock_acquisition() -> None:
    """Scenario: A heartbeat refreshed while locking makes the run ineligible."""
    service, store, audit, notifier, lock = _service(StuckKind.STALE_RUNNING)
    fresh = replace(
        store.snapshot,
        project=replace(store.snapshot.project, heartbeat_at=NOW),
    )
    store.snapshots = [store.snapshot, fresh]
    result = await service.reprocess(_command())
    assert result.refusal is RefusalCode.FRESH_RUNNING
    assert lock.held == [["autopilot:r1", "project:p1"]]
    assert store.apply_calls == 0
    assert audit.commands == []
    assert notifier.notices == []


async def test_orphan_uses_adopt_mutation_without_graph_dependency() -> None:
    """Scenario: An orphan is adopted without replaying a review decision."""
    service, store, _, _, lock = _service(StuckKind.ORPHAN)
    result = await service.reprocess(_command())
    assert result.outcome is RecoveryOutcome.QUEUED
    assert result.stuck_kind is StuckKind.ORPHAN
    assert store.apply_calls == 1
    assert lock.held == [["project:p1"]]


async def test_capability_is_read_only_and_reports_progress() -> None:
    """Scenario: Workspace capability includes the current run and lock version."""
    service, store, audit, notifier, _ = _service(StuckKind.RETRY_WAIT)
    store.existing = store.write.run
    capability = await service.inspect(_command())
    assert capability.can_reprocess is True
    assert capability.run == store.existing
    assert capability.lock_version == 4
    assert store.apply_calls == 0
    assert audit.commands == []
    assert notifier.notices == []


async def test_missing_target_is_not_a_recovery_id() -> None:
    """Scenario: Projectless unstaged display rows never invent recovery ids."""
    service, store, _, _, _ = _service(StuckKind.ORPHAN)
    store.snapshot = replace(store.snapshot, missing=True)
    result = await service.reprocess(_command(run_id=uuid4()))
    assert result.outcome is RecoveryOutcome.NOT_FOUND
    assert result.run is None
    assert store.apply_calls == 0
