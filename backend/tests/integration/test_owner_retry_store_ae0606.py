"""The owner Retry on a real session: one transaction, nothing on a refusal.

Feature: tests/features/carousel_owner_retry_ae0606.feature
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import update
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.workflow_timeout_repository import (
    WorkflowTimeoutRepository,
)
from rag_backend.infrastructure.events.memory_event_publisher import (
    MemoryEventPublisher,
)
from rag_backend.modules.autopilot.domain.carousel_retry import CarouselRetryRequest
from rag_backend.modules.autopilot.infrastructure.carousel_retrier import (
    QueueCarouselRetrier,
)
from rag_backend.modules.autopilot.infrastructure.models import AutopilotRunModel
from rag_backend.modules.editorial.public import AutomationRun, claim_automation_phase
from rag_backend.modules.generation_queue.application.owner_retry import (
    OwnerRetryDependencies,
    OwnerRetryService,
)
from rag_backend.modules.generation_queue.domain.models import GenerationStatus
from rag_backend.modules.generation_queue.domain.owner_retry import (
    OwnerRetryCommand,
    RetryFacts,
    RetryKind,
    RetryRefusal,
    RetrySurface,
)
from rag_backend.modules.generation_queue.infrastructure.owner_retry_audit import (
    SqlOwnerRetryAudit,
)
from rag_backend.modules.generation_queue.infrastructure.owner_retry_facts import (
    OwnerRetryFacts,
)
from rag_backend.modules.generation_queue.infrastructure.owner_retry_store import (
    SqlOwnerRetryStore,
)
from rag_backend.modules.generation_queue.retry_public import build_owner_retry
from tests.integration.manual_reprocess_support import (
    NOW,
    project_row,
    workflow_run_row,
)
from tests.integration.owner_retry_support import (
    OWNER_ID,
    FakeEngine,
    autopilot_state,
    record_run_starts,
    retry_audits,
    retry_engine,
    seed_autopilot,
    seed_owner,
    staged_runs,
)
from tests.integration.pg_schema_support import requires_postgres

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _relay_disabled(no_outbox_relay: object) -> None:
    del no_outbox_relay


@pytest.fixture
def run_starts(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    return record_run_starts(monkeypatch)


@pytest_asyncio.fixture(loop_scope="function")
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    async with retry_engine(tmp_path) as built:
        yield built


def _sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def _state(phase: str, **extra: object) -> dict[str, object]:
    return {"current_phase": phase, "phase_status": "awaiting_human", **extra}


async def _seed(session: AsyncSession, project_id: str, **overrides: object) -> None:
    values: dict[str, object] = {
        "phase_status": "failed",
        "status": "failed",
        "run_heartbeat_at": None,
    }
    values.update(overrides)
    await seed_owner(session)
    session.add(project_row(project_id, owner_id=OWNER_ID, **values))
    await session.commit()


def _web(project_id: str, version: int | None = 4) -> OwnerRetryCommand:
    return OwnerRetryCommand(
        project_id=project_id,
        actor_id=OWNER_ID,
        surface=RetrySurface.WEB,
        expected_version=version,
    )


async def _row(session: AsyncSession, project_id: str) -> CarouselProjectModel:
    row = await session.get(CarouselProjectModel, project_id, populate_existing=True)
    assert row is not None
    return row


# Scenario: A failed phase parked before its node is re-driven
async def test_a_parked_failed_phase_is_redriven(
    engine: AsyncEngine, run_starts: list[str]
) -> None:
    project_id = "11111111-1111-4111-8111-111111111111"
    fake = FakeEngine(state=_state("outline"), parked=True)
    async with _sessions(engine)() as session:
        await _seed(session, project_id, current_phase="outline")
        result = await build_owner_retry(session, fake.typed()).retry(_web(project_id))
        runs = await staged_runs(session, project_id)
        audits = await retry_audits(session)
        row = await _row(session, project_id)
    assert result.accepted is True
    assert result.kind is RetryKind.REDRIVE
    assert result.lock_version == 5
    assert row.phase_status == "in_progress"
    assert row.lock_version == 5
    assert [r.dedupe_key for r in runs] == [f"resume:{project_id}:5"]
    assert runs[0].payload["action"] == "redrive"
    assert runs[0].payload["feedback"] is None
    assert runs[0].payload["reviewer_id"] == OWNER_ID
    assert len(audits) == 1
    assert audits[0].payload["retry_kind"] == "redrive"
    assert audits[0].payload["surface"] == "web"
    assert audits[0].payload["previous_phase_status"] == "failed"
    assert audits[0].payload["lock_version"] == 5
    assert audits[0].payload["feedback"] == ""
    assert run_starts == [
        f"phase:{project_id}:outline:in_progress",
        f"run.started:{project_id}:outline",
    ]


# Scenario: An escalated autopilot run moves back to generating
async def test_an_escalated_run_moves_back_to_generating(
    engine: AsyncEngine, run_starts: list[str]
) -> None:
    project_id = "22222222-2222-4222-8222-222222222222"
    fake = FakeEngine(state=_state("content"))
    async with _sessions(engine)() as session:
        await _seed(session, project_id, phase_status="awaiting_human")
        run_id = await seed_autopilot(
            session, project_id, "escalated", "persona_score_below_threshold"
        )
        await session.commit()
        retrier = QueueCarouselRetrier(session, fake.typed)
        outcome = await retrier.retry(
            CarouselRetryRequest(project_id=project_id, actor_id=OWNER_ID)
        )
        before_commit = list(run_starts)
        await session.commit()
        await retrier.deliver()
        await retrier.deliver()
        runs = await staged_runs(session, project_id)
        audits = await retry_audits(session)
        state = await autopilot_state(session, run_id)
    assert outcome.accepted is True
    assert outcome.phase == "content"
    assert before_commit == []
    assert run_starts == [
        f"phase:{project_id}:content:in_progress",
        f"run.started:{project_id}:content",
    ]
    assert state == ("generating", "owner_carousel_retry")
    assert runs[0].payload["action"] == "revise"
    line = str(runs[0].payload["feedback"])
    assert "Reason: persona_score_below_threshold." in line
    assert runs[0].payload["structured_feedback"] == {"feedback_source": "autopilot"}
    assert audits[0].payload["feedback"] == line
    assert audits[0].payload["surface"] == "telegram"
    assert audits[0].payload["autopilot_run_id"] == str(run_id)


# Scenario: Retry on a rejected carousel re-runs the phase it was rejected at
# Scenario: A closed autopilot run leaves the run alone and re-runs the carousel only
async def test_a_rejected_gate_is_revised_and_its_status_restored(
    engine: AsyncEngine,
) -> None:
    project_id = "33333333-3333-4333-8333-333333333333"
    fake = FakeEngine(state=_state("content"))
    async with _sessions(engine)() as session:
        await _seed(session, project_id, phase_status="rejected")
        run_id = await seed_autopilot(
            session, project_id, "rejected", "escalation_expired"
        )
        await session.commit()
        result = await build_owner_retry(session, fake.typed()).retry(_web(project_id))
        runs = await staged_runs(session, project_id)
        row = await _row(session, project_id)
        state = await autopilot_state(session, run_id)
    assert result.kind is RetryKind.REVISE
    assert result.autopilot_run_id is None
    assert row.status == "pending"
    assert row.phase_status == "in_progress"
    assert "Reason: carousel_rejected." in str(runs[0].payload["feedback"])
    assert state == ("rejected", "escalation_expired")


# Scenario: Retry on a carousel rejected at the final review reopens the review
async def test_a_rejected_final_review_is_reopened(engine: AsyncEngine) -> None:
    project_id = "44444444-4444-4444-8444-444444444444"
    fake = FakeEngine(state=_state("final_review"))
    async with _sessions(engine)() as session:
        await _seed(
            session, project_id, current_phase="final_review", phase_status="rejected"
        )
        result = await build_owner_retry(session, fake.typed()).retry(_web(project_id))
        runs = await staged_runs(session, project_id)
        audits = await retry_audits(session)
        row = await _row(session, project_id)
    assert result.kind is RetryKind.REOPEN
    assert runs == []
    assert row.phase_status == "awaiting_human"
    assert row.current_phase == "final_review"
    assert row.status == "completed"
    assert row.lock_version == 5
    assert audits[0].payload["retry_kind"] == "reopen"


# Scenario: A double tap ends in run_in_progress
async def test_a_second_retry_is_refused_as_in_progress(engine: AsyncEngine) -> None:
    project_id = "55555555-5555-4555-8555-555555555555"
    fake = FakeEngine(state=_state("content"))
    async with _sessions(engine)() as session:
        await _seed(session, project_id)
        first = await build_owner_retry(session, fake.typed()).retry(_web(project_id))
        second = await build_owner_retry(session, fake.typed()).retry(
            _web(project_id, 5)
        )
        runs = await staged_runs(session, project_id)
    assert first.accepted is True
    assert second.refusal is RetryRefusal.RUN_IN_PROGRESS
    assert len(runs) == 1


# Scenario: A revise at the revision cap is refused
async def test_a_revise_at_the_cap_is_refused(engine: AsyncEngine) -> None:
    project_id = "66666666-6666-4666-8666-666666666666"
    fake = FakeEngine(state=_state("content", revision_count={"content": 5}))
    async with _sessions(engine)() as session:
        await _seed(session, project_id)
        result = await build_owner_retry(session, fake.typed()).retry(_web(project_id))
        runs = await staged_runs(session, project_id)
        row = await _row(session, project_id)
    assert result.refusal is RetryRefusal.REVISION_CAP_EXCEEDED
    assert runs == []
    assert (row.phase_status, row.lock_version) == ("failed", 4)


# Scenario: A retry sent with the version read before an auto-reject is refused
async def test_a_stale_version_is_refused_with_nothing_written(
    engine: AsyncEngine,
) -> None:
    project_id = "77777777-7777-4777-8777-777777777777"
    fake = FakeEngine(state=_state("content"))
    async with _sessions(engine)() as session:
        await _seed(session, project_id, phase_status="rejected", lock_version=5)
        result = await build_owner_retry(session, fake.typed()).retry(_web(project_id))
        runs = await staged_runs(session, project_id)
        audits = await retry_audits(session)
        row = await _row(session, project_id)
    assert result.refusal is RetryRefusal.VERSION_CONFLICT
    assert runs == []
    assert audits == []
    assert (row.phase_status, row.status, row.lock_version) == (
        "rejected",
        "failed",
        5,
    )


class _RacingStore(SqlOwnerRetryStore):
    """Another request moves the escalated run right after the facts are read."""

    async def read(self, command: OwnerRetryCommand) -> RetryFacts | None:
        facts = await super().read(command)
        await self._session.execute(
            update(AutopilotRunModel)
            .where(AutopilotRunModel.carousel_project_id == command.project_id)
            .values(state="awaiting_owner")
        )
        return facts


# Scenario: A lost autopilot run compare-and-set rolls back the stage and the audit
async def test_a_lost_run_move_rolls_everything_back(
    engine: AsyncEngine, run_starts: list[str]
) -> None:
    project_id = "88888888-8888-4888-8888-888888888888"
    fake = FakeEngine(state=_state("content"))
    async with _sessions(engine)() as session:
        await _seed(session, project_id, phase_status="awaiting_human")
        await seed_autopilot(session, project_id, "escalated", "phase_failed")
        await session.commit()
        service = OwnerRetryService(
            OwnerRetryDependencies(
                store=_RacingStore(session, fake.typed()),
                audit=SqlOwnerRetryAudit(session),
            ),
            owns_transaction=False,
        )
        result = await service.retry(_web(project_id))
        runs = await staged_runs(session, project_id)
        audits = await retry_audits(session)
        row = await _row(session, project_id)
    assert result.refusal is RetryRefusal.CONCURRENT_UPDATE
    assert runs == []
    assert audits == []
    assert (row.phase_status, row.lock_version) == ("awaiting_human", 4)
    assert row.run_started_at is None
    assert run_starts == []


# Scenario: A tap from someone who does not own the carousel changes nothing
async def test_a_non_owner_tap_changes_nothing(engine: AsyncEngine) -> None:
    project_id = "99999999-9999-4999-8999-999999999999"
    fake = FakeEngine(state=_state("content"))
    async with _sessions(engine)() as session:
        await _seed(session, project_id, phase_status="awaiting_human")
        run_id = await seed_autopilot(session, project_id, "escalated", "x")
        await session.commit()
        retrier = QueueCarouselRetrier(session, fake.typed)
        outcome = await retrier.retry(
            CarouselRetryRequest(project_id=project_id, actor_id="someone-else")
        )
        retrier.discard()
        await retrier.deliver()
        runs = await staged_runs(session, project_id)
        state = await autopilot_state(session, run_id)
    assert outcome.accepted is False
    assert outcome.refusal == "not_owner"
    assert runs == []
    assert state == ("escalated", "x")


# Scenario: A carousel without a checkpoint is refused with no_checkpoint
async def test_a_missing_checkpoint_is_refused(engine: AsyncEngine) -> None:
    project_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    async with _sessions(engine)() as session:
        await _seed(session, project_id, phase_status="rejected")
        result = await build_owner_retry(session, FakeEngine(state=None).typed()).retry(
            _web(project_id)
        )
    assert result.refusal is RetryRefusal.NO_CHECKPOINT


async def test_a_missing_carousel_is_not_found(engine: AsyncEngine) -> None:
    async with _sessions(engine)() as session:
        service = build_owner_retry(session, FakeEngine(state=None).typed())
        result = await service.retry(_web("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"))
    assert result.refusal is RetryRefusal.NOT_FOUND


# Scenario: The retry capability is read without any change
async def test_the_capability_is_read_without_a_write(engine: AsyncEngine) -> None:
    project_id = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    fake = FakeEngine(state=_state("content", persona_scores=[{"overall": 50}]))
    async with _sessions(engine)() as session:
        await _seed(session, project_id)
        capability = await build_owner_retry(session, fake.typed()).inspect(
            _web(project_id, None)
        )
        runs = await staged_runs(session, project_id)
        row = await _row(session, project_id)
    assert capability.can_retry is True
    assert capability.kind is RetryKind.REVISE
    assert runs == []
    assert (row.phase_status, row.lock_version) == ("failed", 4)


# Scenario: An unattended approve on a rejected carousel is refused
async def test_an_unattended_approve_on_a_rejected_carousel_is_refused(
    engine: AsyncEngine,
) -> None:
    project_id = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
    fake = FakeEngine(state=_state("content"))
    async with _sessions(engine)() as session:
        await _seed(session, project_id, phase_status="rejected")
        with pytest.raises(ValueError, match="carousel_rejected"):
            await claim_automation_phase(
                AutomationRun(
                    engine=fake.typed(),
                    session=session,
                    project_id=project_id,
                    expected_version=4,
                    action="approve",
                )
            )
        row = await _row(session, project_id)
    assert (row.phase_status, row.lock_version) == ("rejected", 4)
    assert fake.flipped == []


async def _dead_letter_run(session: AsyncSession, project_id: str) -> None:
    session.add(
        workflow_run_row(
            project_id, GenerationStatus.DEAD_LETTER, finished_at=NOW, id=uuid4()
        )
    )
    await session.commit()


# Scenario: A discarded dead letter no longer blocks the retry
async def test_a_discarded_dead_letter_no_longer_blocks(engine: AsyncEngine) -> None:
    project_id = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
    fake = FakeEngine(state=_state("content"))
    async with _sessions(engine)() as session:
        await _seed(session, project_id)
        await seed_autopilot(session, project_id, "rejected", "owner_queue_discard")
        await _dead_letter_run(session, project_id)
        result = await build_owner_retry(session, fake.typed()).retry(_web(project_id))
    assert result.accepted is True
    assert result.kind is RetryKind.REVISE


# Scenario: A queue dead letter answers use_reprocess
async def test_a_latest_parked_dead_letter_answers_use_reprocess(
    engine: AsyncEngine,
) -> None:
    project_id = "ffffffff-ffff-4fff-8fff-ffffffffffff"
    fake = FakeEngine(state=_state("content"))
    async with _sessions(engine)() as session:
        await _seed(session, project_id)
        await seed_autopilot(
            session, project_id, "escalated", "queue_dead_letter:permanent"
        )
        await _dead_letter_run(session, project_id)
        result = await build_owner_retry(session, fake.typed()).retry(_web(project_id))
    assert result.refusal is RetryRefusal.USE_REPROCESS


@dataclass
class _OrigError(Exception):
    sqlstate: str


# Scenario: A lost lock is refused as concurrent_update
@pytest.mark.parametrize("sqlstate", ["40P01", "40001", "55P03"])
async def test_a_lost_lock_is_a_concurrent_update(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch, sqlstate: str
) -> None:
    project_id = "12121212-1212-4212-8212-121212121212"

    async def _deadlock(self: object, command: OwnerRetryCommand) -> None:
        del self, command
        raise OperationalError("SELECT ... FOR UPDATE", {}, _OrigError(sqlstate))

    monkeypatch.setattr(OwnerRetryFacts, "read", _deadlock)
    async with _sessions(engine)() as session:
        await _seed(session, project_id)
        result = await build_owner_retry(
            session, FakeEngine(state=_state("content")).typed()
        ).retry(_web(project_id))
        row = await _row(session, project_id)
    assert result.refusal is RetryRefusal.CONCURRENT_UPDATE
    assert row.phase_status == "failed"


async def test_any_other_database_error_still_raises(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _broken(self: object, command: OwnerRetryCommand) -> None:
        del self, command
        raise OperationalError("SELECT 1", {}, _OrigError("08006"))

    monkeypatch.setattr(OwnerRetryFacts, "read", _broken)
    async with _sessions(engine)() as session:
        service = build_owner_retry(session, FakeEngine(state=None).typed())
        with pytest.raises(OperationalError):
            await service.retry(_web("13131313-1313-4313-8313-131313131313"))


# Scenario: The retry capability shows a revise at the cap as refused
async def test_the_capability_at_the_revision_cap_is_refused(
    engine: AsyncEngine,
) -> None:
    project_id = "14141414-1414-4414-8414-141414141414"
    fake = FakeEngine(state=_state("content", revision_count={"content": 5}))
    async with _sessions(engine)() as session:
        await _seed(session, project_id)
        capability = await build_owner_retry(session, fake.typed()).inspect(
            _web(project_id, None)
        )
    assert capability.can_retry is False
    assert capability.refusal is RetryRefusal.REVISION_CAP_EXCEEDED


# Scenario: A stuck sweep never rejects a carousel a Retry just started
async def test_the_sweep_skips_a_carousel_retried_after_its_read(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id = "15151515-1515-4515-8515-151515151515"
    fake = FakeEngine(state=_state("content"), parked=True)
    sessions = _sessions(engine)
    async with sessions() as session:
        await _seed(
            session,
            project_id,
            phase_status="awaiting_human",
            status="pending",
            updated_at=NOW - timedelta(hours=80),
        )
    original = WorkflowTimeoutRepository._find_stuck

    async def _read_then_retry(
        db: AsyncSession, cutoff: datetime
    ) -> list[CarouselProjectModel]:
        found = await original(db, cutoff)
        async with sessions() as other:
            accepted = await build_owner_retry(other, fake.typed()).retry(
                _web(project_id)
            )
        assert accepted.accepted is True
        return found

    monkeypatch.setattr(
        WorkflowTimeoutRepository, "_find_stuck", staticmethod(_read_then_retry)
    )
    async with sessions() as session:
        repository = WorkflowTimeoutRepository(
            WorkflowEventService(MemoryEventPublisher())
        )
        rejected = await repository.auto_reject_stuck(session, 72)
        await session.commit()
        row = await _row(session, project_id)
    assert rejected == 0
    assert (row.phase_status, row.lock_version) == ("in_progress", 5)


# Scenario: A second retry waits on the row lock and then answers run_in_progress
@requires_postgres
async def test_a_concurrent_second_retry_waits_and_is_refused(
    engine: AsyncEngine,
) -> None:
    project_id = "16161616-1616-4616-8616-161616161616"
    fake = FakeEngine(state=_state("content"))
    sessions = _sessions(engine)
    async with sessions() as session:
        await _seed(session, project_id)
    async with sessions() as first, sessions() as second:
        accepted = await build_owner_retry(
            first, fake.typed(), owns_transaction=False
        ).retry(_web(project_id))
        waiting = asyncio.create_task(
            build_owner_retry(second, fake.typed()).retry(_web(project_id))
        )
        await asyncio.sleep(0.5)
        blocked = not waiting.done()
        await first.commit()
        refused = await waiting
        runs = await staged_runs(first, project_id)
    assert accepted.accepted is True
    assert blocked is True
    assert refused.refusal is RetryRefusal.RUN_IN_PROGRESS
    assert len(runs) == 1
