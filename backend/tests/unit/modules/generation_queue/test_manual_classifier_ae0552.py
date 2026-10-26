"""Stuck-only classification for owner-driven carousel recovery."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_PENDING,
)
from rag_backend.modules.generation_queue.domain.manual_recovery import (
    ManualReprocessCommand,
    ProjectRecoveryState,
    RecoveryPolicy,
    RecoverySnapshot,
    RefusalCode,
    StuckKind,
    recovery_lock_keys,
)
from rag_backend.modules.generation_queue.domain.manual_recovery_classifier import (
    classify_recovery,
)
from rag_backend.modules.generation_queue.domain.models import (
    GenerationKind,
    GenerationRun,
    GenerationStatus,
    is_active,
)
from tests.unit.modules.generation_queue.queue_fakes import make_run, resume_run

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
POLICY = RecoveryPolicy(heartbeat_stale_seconds=180, dispatcher_grace_seconds=600)


def _project(**overrides: object) -> ProjectRecoveryState:
    project = ProjectRecoveryState(
        id="p1",
        title="Theme",
        phase_status=PHASE_STATUS_IN_PROGRESS,
        lock_version=4,
        heartbeat_at=NOW,
        updated_at=NOW - timedelta(seconds=601),
    )
    return replace(project, **overrides)


def _command(**overrides: object) -> ManualReprocessCommand:
    command = ManualReprocessCommand(
        project_id="p1", run_id=None, actor_id="owner", expected_version=4
    )
    return replace(command, **overrides)


_UNSET = object()


def _snapshot(
    run: GenerationRun | None = None,
    project: object = _UNSET,
    **overrides: object,
) -> RecoverySnapshot:
    selected_project = _project() if project is _UNSET else project
    active_id = run.id if run is not None and is_active(run.status) else None
    snapshot = RecoverySnapshot(
        command=_command(),
        run=run,
        project=selected_project,
        latest_run_id=run.id if run is not None else None,
        active_run_id=active_id,
    )
    return replace(snapshot, **overrides)


@pytest.mark.parametrize(
    ("run", "expected"),
    [
        (make_run(status=GenerationStatus.DEAD_LETTER), StuckKind.DEAD_LETTER),
        (make_run(status=GenerationStatus.RETRY_WAIT), StuckKind.RETRY_WAIT),
        (
            make_run(status=GenerationStatus.RUNNING),
            StuckKind.STALE_RUNNING,
        ),
    ],
)
def test_run_stuck_kinds(run: object, expected: StuckKind) -> None:
    """Scenario: Dead letters, retry waits and stale running rows are recoverable."""
    if expected is StuckKind.STALE_RUNNING:
        run = replace(run, status=GenerationStatus.RUNNING)
        snapshot = _snapshot(run, _project(heartbeat_at=NOW - timedelta(seconds=181)))
    else:
        snapshot = _snapshot(run)
    decision = classify_recovery(snapshot, NOW, POLICY)
    assert decision.stuck is expected
    assert decision.refusal is None


def test_orphan_after_dispatcher_grace() -> None:
    """Scenario: A generating project with no active run is adopted."""
    snapshot = _snapshot(run=None, active_run_id=None)
    assert classify_recovery(snapshot, NOW, POLICY).stuck is StuckKind.ORPHAN


@pytest.mark.parametrize(
    ("snapshot", "refusal"),
    [
        (
            _snapshot(
                run=None, project=_project(phase_status=PHASE_STATUS_AWAITING_HUMAN)
            ),
            RefusalCode.OWNER_WAITING,
        ),
        (
            _snapshot(make_run(status=GenerationStatus.QUEUED)),
            RefusalCode.NORMAL_QUEUED,
        ),
        (
            _snapshot(run=None, active_run_id=None, project=_project(updated_at=NOW)),
            RefusalCode.DISPATCHER_GRACE,
        ),
        (
            _snapshot(make_run(status=GenerationStatus.RUNNING)),
            RefusalCode.FRESH_RUNNING,
        ),
        (
            _snapshot(
                make_run(status=GenerationStatus.RUNNING),
                _project(heartbeat_at=None),
            ),
            RefusalCode.NULL_HEARTBEAT,
        ),
        (
            _snapshot(run=None, project=_project(phase_status=PHASE_STATUS_PENDING)),
            RefusalCode.UNSUPPORTED,
        ),
        (
            _snapshot(
                make_run(status=GenerationStatus.DEAD_LETTER),
                command=_command(expected_version=3),
            ),
            RefusalCode.STALE_VERSION,
        ),
        (
            _snapshot(
                make_run(status=GenerationStatus.DEAD_LETTER),
                latest_run_id=uuid4(),
            ),
            RefusalCode.UNSUPPORTED,
        ),
        (
            _snapshot(
                make_run(status=GenerationStatus.DEAD_LETTER),
                active_run_id=uuid4(),
            ),
            RefusalCode.NORMAL_QUEUED,
        ),
        (
            _snapshot(
                make_run(status=GenerationStatus.DEAD_LETTER),
                autopilot_dead=False,
            ),
            RefusalCode.UNSUPPORTED,
        ),
        (
            _snapshot(
                run=None,
                project=None,
                command=_command(project_id=None),
                active_run_id=None,
            ),
            RefusalCode.PROJECTLESS_UNSTAGED,
        ),
    ],
)
def test_refusals(snapshot: RecoverySnapshot, refusal: RefusalCode) -> None:
    """Scenario: Not stuck work is refused with a stable reason."""
    decision = classify_recovery(snapshot, NOW, POLICY)
    assert decision.stuck is None
    assert decision.refusal is refusal


def test_terminal_run_can_still_be_an_orphan_after_grace() -> None:
    """Scenario: A generating project with no active run is adopted."""
    run = make_run(status=GenerationStatus.SUCCEEDED)
    snapshot = _snapshot(run, active_run_id=None)
    assert classify_recovery(snapshot, NOW, POLICY).stuck is StuckKind.ORPHAN


def test_heartbeat_exactly_at_threshold_is_fresh() -> None:
    """Scenario: A running row is stale only beyond the reaper threshold."""
    snapshot = _snapshot(
        make_run(status=GenerationStatus.RUNNING),
        _project(heartbeat_at=NOW - timedelta(seconds=180)),
    )
    assert classify_recovery(snapshot, NOW, POLICY).refusal is RefusalCode.FRESH_RUNNING


def test_complete_autopilot_lock_set_uses_current_project() -> None:
    """Scenario: A stale running takeover fences the run and attributed project."""
    run = make_run(status=GenerationStatus.RUNNING)
    snapshot = _snapshot(run, _project(id="current-project"))
    assert recovery_lock_keys(snapshot) == ["autopilot:r1", "project:current-project"]


def test_workflow_lock_set_uses_project_builder() -> None:
    """Scenario: A workflow takeover uses the executor's project lock key."""
    run = resume_run(status=GenerationStatus.RUNNING)
    snapshot = _snapshot(run)
    assert recovery_lock_keys(snapshot) == ["project:p1"]


def test_orphan_lock_set_never_invents_an_autopilot_key() -> None:
    """Scenario: An orphan adoption locks only the generating project."""
    snapshot = _snapshot(run=None, active_run_id=None)
    assert recovery_lock_keys(snapshot) == ["project:p1"]


def test_project_backed_unstaged_autopilot_uses_complete_lock_set() -> None:
    """Scenario: An abandoned staged-project autopilot run is recovered safely."""
    snapshot = _snapshot(
        run=None,
        active_run_id=None,
        autopilot_run_id="a1",
        autopilot_state="generating",
    )
    assert classify_recovery(snapshot, NOW, POLICY).stuck is StuckKind.ORPHAN
    assert recovery_lock_keys(snapshot) == ["autopilot:a1", "project:p1"]


def test_projectless_unstaged_autopilot_never_gets_recovery_keys() -> None:
    """Scenario: A projectless unstaged row remains display-only."""
    snapshot = _snapshot(
        run=None,
        project=None,
        command=_command(project_id=None),
        active_run_id=None,
        autopilot_run_id="a1",
        autopilot_state="queued",
    )
    decision = classify_recovery(snapshot, NOW, POLICY)
    assert decision.refusal is RefusalCode.PROJECTLESS_UNSTAGED
    assert recovery_lock_keys(snapshot) == []


def test_unstaged_autopilot_owner_wait_is_not_an_orphan() -> None:
    """Scenario: Owner waiting is refused even without a staged generation row."""
    snapshot = _snapshot(
        run=None,
        active_run_id=None,
        autopilot_run_id="a1",
        autopilot_state="awaiting_owner",
    )
    assert classify_recovery(snapshot, NOW, POLICY).refusal is RefusalCode.OWNER_WAITING


def test_missing_autopilot_identity_cannot_take_over() -> None:
    """Scenario: Malformed autopilot work is unsupported rather than under-locked."""
    run = make_run(
        kind=GenerationKind.AUTOPILOT_DRIVE,
        autopilot_run_id=None,
        status=GenerationStatus.RUNNING,
    )
    snapshot = _snapshot(run, _project(heartbeat_at=NOW - timedelta(seconds=181)))
    assert recovery_lock_keys(snapshot) == []
    assert classify_recovery(snapshot, NOW, POLICY).refusal is RefusalCode.UNSUPPORTED
