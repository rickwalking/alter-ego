"""An abandoned escalation that closes also settles its carousel, on Postgres.

Feature: tests/features/escalation_close_settles_carousel_ae0601.feature. The
run repository, the recovery store, the carousel settler (editorial facade, the
stuck auto-reject's transition, the workflow event service) and the row lock
are real; only the gate read is a fake, since no workflow checkpoint exists.
Skipped without a Postgres ``DATABASE_URL``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_PUBLISHED,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_REJECTED,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.constants.workflow_events import (
    AGGREGATE_TYPE_PROJECT,
    EVENT_TYPE_PROJECT_PHASE_CHANGED,
)
from rag_backend.domain.constants.workflow_timeout import (
    AUTO_REJECT_CAROUSEL_STATUS,
    ESCALATION_EXPIRED_EVENT_SOURCE,
    ESCALATION_EXPIRED_REJECT_MESSAGE,
)
from rag_backend.infrastructure.database import workflow_timeout_repository
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.modules.autopilot.application.publish_job import SystemClock
from rag_backend.modules.autopilot.application.run_recovery import (
    RecoveryDependencies,
    RunRecovery,
)
from rag_backend.modules.autopilot.constants import GATE_CONTENT
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.carousel_settler import (
    carousel_settler,
)
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)
from rag_backend.modules.autopilot.infrastructure.repository import (
    SqlAlchemyAutopilotRepository,
)
from rag_backend.modules.autopilot.infrastructure.run_recovery_store import (
    SqlRunRecoveryStore,
)
from rag_backend.modules.autopilot.recovery_constants import (
    OWNER_REVIEW_EXPIRY_HOURS,
    REASON_ESCALATION_EXPIRED,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres
from tests.unit.modules.autopilot.test_autopilot_runner import _Notices, _snapshot
from tests.unit.modules.autopilot.test_qa_r2_escalation import _PerProject

pytestmark = pytest.mark.usefixtures("no_outbox_relay")

_VERSION = 4
_ROOTS = ("autopilot_runs", "event_outbox", "workflow_audit_log")


def _tables() -> list[str]:
    """The roots plus every table their foreign keys reach, referenced first."""
    ordered: list[str] = []

    def _visit(name: str) -> None:
        if name in ordered:
            return
        for key in Base.metadata.tables[name].foreign_keys:
            target = key.column.table.name
            if target != name:
                _visit(target)
        ordered.append(name)

    for root in _ROOTS:
        _visit(root)
    return ordered


def _sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def _seed(engine: AsyncEngine, **carousel: object) -> tuple[str, UUID]:
    """A carousel waiting at the content gate and its run, escalated 73 hours ago."""
    project_id, topic_id, run_id = str(uuid4()), uuid4(), uuid4()
    stale = datetime.now(UTC) - timedelta(hours=OWNER_REVIEW_EXPIRY_HOURS + 1)
    fields: dict[str, object] = {
        "status": "generating",
        "current_phase": PHASE_CONTENT,
        "phase_status": PHASE_STATUS_AWAITING_HUMAN,
        "workflow_status": "draft",
        "lock_version": _VERSION,
        **carousel,
    }
    async with _sessions(engine)() as session:
        session.add(
            CarouselProjectModel(
                id=project_id, topic="Agentes", audience="Devs", niche="IA", **fields
            )
        )
        await session.flush()
        await session.execute(
            insert(TopicCandidateModel).values(
                id=topic_id,
                title="t",
                angle="a",
                why_viral="w",
                audience="a",
                niche="tech",
                brief="b",
                sources=[],
                score=1,
                signal_hash=topic_id.hex,
                status="used",
            )
        )
        await session.execute(
            insert(AutopilotRunModel).values(
                id=run_id,
                carousel_project_id=project_id,
                topic_candidate_id=topic_id,
                state=AutopilotRunState.ESCALATED.value,
                escalated_version=_VERSION,
                telegram_message_ids=[],
                created_at=stale,
                updated_at=stale,
            )
        )
        await session.commit()
    return project_id, run_id


async def _sweep(engine: AsyncEngine, project_id: str) -> int:
    """One recovery sweep on its own session, committed like the worker tick."""
    editorial = _PerProject()
    editorial.snapshots[project_id] = _snapshot(GATE_CONTENT, 90.0, 0)
    async with _sessions(engine)() as session:
        repo = SqlAlchemyAutopilotRepository(session)
        recovery = RunRecovery(
            RecoveryDependencies(
                runs=repo,
                editorial=editorial,
                notices=_Notices(),
                recovery=SqlRunRecoveryStore(session),
                clock=SystemClock(),
                notifier_configured=True,
                carousels=carousel_settler(session),
            )
        )
        moved = await recovery.sweep()
        await session.commit()
    return moved


async def _run(engine: AsyncEngine, run_id: UUID) -> AutopilotRunModel:
    async with _sessions(engine)() as session:
        row = await session.get(AutopilotRunModel, run_id)
        assert row is not None
        return row


async def _carousel(engine: AsyncEngine, project_id: str) -> CarouselProjectModel:
    async with _sessions(engine)() as session:
        row = await session.get(CarouselProjectModel, project_id)
        assert row is not None
        return row


async def _phase_events(engine: AsyncEngine, project_id: str) -> list[EventOutboxModel]:
    async with _sessions(engine)() as session:
        result = await session.execute(
            select(EventOutboxModel).where(
                EventOutboxModel.aggregate_id == project_id,
                EventOutboxModel.aggregate_type == AGGREGATE_TYPE_PROJECT,
                EventOutboxModel.event_type == EVENT_TYPE_PROJECT_PHASE_CHANGED,
            )
        )
        return list(result.scalars().all())


async def _assert_closed(engine: AsyncEngine, run_id: UUID) -> None:
    run = await _run(engine, run_id)
    assert (run.state, run.state_reason) == (
        AutopilotRunState.REJECTED.value,
        REASON_ESCALATION_EXPIRED,
    )


# Scenario: Closing an abandoned escalation rejects its waiting carousel
# Scenario: A second sweep does nothing
@requires_postgres
@pytest.mark.asyncio
async def test_closing_an_abandoned_escalation_rejects_its_carousel() -> None:
    async with isolated_schema(_tables()) as engine:
        project_id, run_id = await _seed(engine)

        assert await _sweep(engine, project_id) == 1

        await _assert_closed(engine, run_id)
        carousel = await _carousel(engine, project_id)
        assert carousel.phase_status == PHASE_STATUS_REJECTED
        assert carousel.status == AUTO_REJECT_CAROUSEL_STATUS
        assert carousel.error_message == ESCALATION_EXPIRED_REJECT_MESSAGE
        assert carousel.lock_version == _VERSION + 1
        events = await _phase_events(engine, project_id)
        assert len(events) == 1
        assert events[0].payload == {
            "previous_phase": PHASE_CONTENT,
            "previous_phase_status": PHASE_STATUS_AWAITING_HUMAN,
            "phase_status": PHASE_STATUS_REJECTED,
            "reason": ESCALATION_EXPIRED_REJECT_MESSAGE,
            "timeout_hours": OWNER_REVIEW_EXPIRY_HOURS,
        }
        assert events[0].metadata_json["source"] == ESCALATION_EXPIRED_EVENT_SOURCE

        assert await _sweep(engine, project_id) == 0
        assert len(await _phase_events(engine, project_id)) == 1


_LEFT_ALONE: dict[str, dict[str, object]] = {
    "already_rejected": {"phase_status": PHASE_STATUS_REJECTED},
    "failed": {"phase_status": PHASE_STATUS_FAILED},
    "approved": {"workflow_status": WORKFLOW_STATUS_APPROVED_FOR_PUBLISH},
    "public": {"is_public": True},
    "published": {"current_phase": PHASE_PUBLISHED},
    "archived": {"archived_at": datetime.now(UTC)},
    "changed_since": {"lock_version": _VERSION + 1},
}


# Scenario: A carousel that is no longer waiting for a human is left alone
# Scenario: A carousel changed since the escalation is left alone
@requires_postgres
@pytest.mark.asyncio
@pytest.mark.parametrize("case", sorted(_LEFT_ALONE))
async def test_a_carousel_not_waiting_unchanged_is_left_alone(case: str) -> None:
    async with isolated_schema(_tables()) as engine:
        project_id, run_id = await _seed(engine, **_LEFT_ALONE[case])
        before = await _carousel(engine, project_id)

        assert await _sweep(engine, project_id) == 1

        await _assert_closed(engine, run_id)
        after = await _carousel(engine, project_id)
        assert (after.phase_status, after.status, after.error_message) == (
            before.phase_status,
            before.status,
            before.error_message,
        )
        assert await _phase_events(engine, project_id) == []


# Scenario: A failed carousel settle still closes the run
@requires_postgres
@pytest.mark.asyncio
async def test_a_failed_settle_rolls_back_only_the_carousel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _half_written(
        _self: object, _db: AsyncSession, project: CarouselProjectModel, _cause: object
    ) -> None:
        project.phase_status = PHASE_STATUS_REJECTED
        raise RuntimeError("event store down")

    monkeypatch.setattr(
        workflow_timeout_repository.WorkflowTimeoutRepository, "reject", _half_written
    )
    async with isolated_schema(_tables()) as engine:
        project_id, run_id = await _seed(engine)

        assert await _sweep(engine, project_id) == 1

        await _assert_closed(engine, run_id)
        carousel = await _carousel(engine, project_id)
        assert carousel.phase_status == PHASE_STATUS_AWAITING_HUMAN
        assert await _phase_events(engine, project_id) == []


# Scenario: A run whose close loses the race settles nothing
@requires_postgres
@pytest.mark.asyncio
async def test_a_run_another_worker_closed_settles_nothing() -> None:
    async with isolated_schema(_tables()) as engine:
        project_id, run_id = await _seed(engine)
        async with _sessions(engine)() as session:
            await session.execute(
                update(AutopilotRunModel)
                .where(AutopilotRunModel.id == run_id)
                .values(state=AutopilotRunState.REJECTED.value)
            )
            await session.commit()

        assert await _sweep(engine, project_id) == 0

        carousel = await _carousel(engine, project_id)
        assert carousel.phase_status == PHASE_STATUS_AWAITING_HUMAN
        assert await _phase_events(engine, project_id) == []
