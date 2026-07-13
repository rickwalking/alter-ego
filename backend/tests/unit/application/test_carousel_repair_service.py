"""Unit tests for the carousel repair service two-commit contract (AE-0311).

Gherkin: tests/features/carousel_deterministic_repair.feature

SQLite convention: the advisory lock no-ops on non-Postgres, so lock
serialization is exercised with an injected-lock double; the CAS, projection
commit, and audit are exercised against a real in-memory session.
"""

from __future__ import annotations

import contextlib
import uuid
from collections.abc import AsyncIterator
from typing import cast

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.application.services.carousel import carousel_repair_service
from rag_backend.application.services.carousel.carousel_repair_service import (
    CarouselRepairDeps,
    CarouselRepairService,
    RepairCarouselCommand,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.carousel_conflicts import (
    CONFLICT_CODE_MUTATION_IN_PROGRESS,
    CONFLICT_CODE_RUN_IN_PROGRESS,
    CONFLICT_CODE_VERSION_CONFLICT,
)
from rag_backend.domain.constants.carousel_repair import (
    REPAIR_STATUS_NOOP,
    REPAIR_STATUS_REPAIRED,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.models.carousel_conflict import (
    CarouselConflict,
    CarouselConflictError,
)
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.models.carousel import (
    CarouselProjectModel,
    CarouselSlideModel,
)
from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.infrastructure.database.models.workflow_audit_log import (
    WorkflowAuditLogModel,
)

_V1 = "hero_lower_third_v1"
_RAW_SCAFFOLD_BODY = (
    "## PT\n**Heading:** O disparo silencioso\n**Body:** A verdade incomoda: "
    "equipes tratam a regeneracao de conteudo como uma operacao segura, mas cada "
    "nova rodada reescreve artefatos ja aprovados pelo revisor humano. Quando o "
    "parser falha, o texto bruto inteiro vaza para o corpo visivel do slide e "
    "ninguem percebe ate a fase de design apontar as violacoes.\n**Features:**\n"
    "- Regeneracao segura\n## EN\n**Heading:** The silent regeneration\n**Body:** x."
)


def _scaffold_localized() -> dict[str, object]:
    return {
        "slide_index": 4,
        "slide_type": "content",
        "presentation_pt": {
            "slide_type": "content",
            "heading": "O disparo silencioso que corrompeu o slide quatro",
            "body": _RAW_SCAFFOLD_BODY,
        },
        "presentation_en": {
            "slide_type": "content",
            "heading": "The silent regeneration that corrupted slide four",
            "body": "The uncomfortable truth about regeneration leaking raw drafts.",
        },
    }


def _blocking_report() -> dict[str, object]:
    return {
        "validation_status": "invalid",
        "validated_at": "2026-07-10T00:00:00Z",
        "blocking": True,
        "violations": [
            {"code": "drafting_scaffold_present", "message": "x", "slide_index": 4}
        ],
    }


class _FakeWorkflow:
    """Checkpoint double: serves a state and records update_state writes."""

    def __init__(self, state: dict[str, object] | None) -> None:
        self.state = state
        self.writes: list[dict[str, object]] = []
        self.fail_write = False

    async def get_workflow_state(self, project_id: str) -> dict[str, object] | None:
        return self.state

    async def update_workflow_state(
        self, project_id: str, values: dict[str, object]
    ) -> None:
        if self.fail_write:
            raise RuntimeError("checkpoint down")
        self.writes.append(values)
        if self.state is not None:
            self.state.update(values)


def _factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_rows(test_engine: AsyncEngine) -> AsyncIterator[None]:
    """The session-scoped SQLite engine commits for real; purge our rows."""
    yield
    async with _factory(test_engine)() as db:
        await db.execute(delete(EventOutboxModel))
        await db.execute(delete(WorkflowAuditLogModel))
        await db.execute(delete(CarouselSlideModel))
        await db.execute(delete(CarouselProjectModel))
        await db.commit()


async def _add_project(
    db: AsyncSession,
    *,
    status: str = "in_review",
    phase_status: str = PHASE_STATUS_AWAITING_HUMAN,
) -> CarouselProjectModel:
    project = CarouselProjectModel(
        id=str(uuid.uuid4()),
        topic="Repair",
        audience="Devs",
        niche="Tech",
        status=status,
        current_phase="design",
        phase_status=phase_status,
        lock_version=1,
        presentation_policy_version=_V1,
    )
    db.add(project)
    await db.flush()
    db.add(
        CarouselSlideModel(
            id=str(uuid.uuid4()),
            project_id=project.id,
            slide_number=4,
            slide_type="content",
            heading="O disparo silencioso que corrompeu o slide quatro",
            body=_RAW_SCAFFOLD_BODY,
            extras={"translation_en": {"heading": "The silent", "body": "truth."}},
        )
    )
    await db.commit()
    return project


def _service(
    db: AsyncSession,
    workflow: _FakeWorkflow,
    *,
    events: WorkflowEventService | None = None,
) -> CarouselRepairService:
    return CarouselRepairService(
        CarouselRepairDeps(
            db=db,
            workflow_service=cast(EditorialWorkflowService, workflow),
            repo=PostgresCarouselRepository(db),
            events=events,
        )
    )


def _command(project: CarouselProjectModel) -> RepairCarouselCommand:
    return RepairCarouselCommand(
        project_id=str(project.id),
        status=str(project.status),
        phase_status=str(project.phase_status or ""),
        lock_version=int(project.lock_version or 1),
        policy_version=_V1,
        actor_user_id="user-1",
    )


async def _slide_body(db: AsyncSession, project_id: str) -> str:
    row = await db.scalar(
        select(CarouselSlideModel).where(CarouselSlideModel.project_id == project_id)
    )
    assert row is not None
    return str(row.body)


@pytest.mark.asyncio
class TestRepairService:
    async def test_in_flight_repairs_both_stores(
        self, test_engine: AsyncEngine
    ) -> None:
        # Scenario: repair strips scaffold in projection + checkpoint.
        async with _factory(test_engine)() as db:
            project = await _add_project(db)
            pid = str(project.id)
            state = {
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
                "presentation_policy_version": _V1,
                "localized_slides": [_scaffold_localized()],
                "presentation_validation": _blocking_report(),
            }
            workflow = _FakeWorkflow(state)
            result = await _service(db, workflow).repair(_command(project))
            assert result.status == REPAIR_STATUS_REPAIRED
            assert result.projection_updated is True
            assert result.checkpoint_updated is True
            assert result.needs_republish is False
            assert result.report["blocking"] is False
            body = await _slide_body(db, pid)
            assert "## PT" not in body and "**Body:**" not in body
            assert workflow.writes and "localized_slides" in workflow.writes[0]

    async def test_idempotent_noop_on_clean_content(
        self, test_engine: AsyncEngine
    ) -> None:
        async with _factory(test_engine)() as db:
            project = await _add_project(db)
            pid = str(project.id)
            state = {
                "phase_status": PHASE_STATUS_AWAITING_HUMAN,
                "presentation_policy_version": _V1,
                "localized_slides": [_scaffold_localized()],
                "presentation_validation": _blocking_report(),
            }
            workflow = _FakeWorkflow(state)
            await _service(db, workflow).repair(_command(project))
            await db.refresh(project)
            second = await _service(db, workflow).repair(_command(project))
            assert second.status == REPAIR_STATUS_NOOP
            assert second.projection_updated is False

    async def test_run_in_progress_rejected(self, test_engine: AsyncEngine) -> None:
        async with _factory(test_engine)() as db:
            project = await _add_project(db, phase_status=PHASE_STATUS_IN_PROGRESS)
            pid = str(project.id)
            workflow = _FakeWorkflow(None)
            with pytest.raises(CarouselConflictError) as exc:
                await _service(db, workflow).repair(_command(project))
            assert exc.value.conflict.code == CONFLICT_CODE_RUN_IN_PROGRESS

    async def test_stale_cas_loses_and_mutates_nothing(
        self, test_engine: AsyncEngine
    ) -> None:
        # Scenario: a concurrent resume bumped lock_version; the repair CAS loses.
        async with _factory(test_engine)() as db:
            project = await _add_project(db)
            pid = str(project.id)
            state = {
                "localized_slides": [_scaffold_localized()],
                "presentation_validation": _blocking_report(),
                "presentation_policy_version": _V1,
            }
            command = RepairCarouselCommand(
                project_id=str(project.id),
                status=str(project.status),
                phase_status=str(project.phase_status or ""),
                lock_version=999,  # stale: the row is at version 1
                policy_version=_V1,
                actor_user_id="user-1",
            )
            with pytest.raises(CarouselConflictError) as exc:
                await _service(db, _FakeWorkflow(state)).repair(command)
            assert exc.value.conflict.code == CONFLICT_CODE_VERSION_CONFLICT
            await db.rollback()
            assert "## PT" in await _slide_body(db, pid)

    async def test_completed_marks_needs_republish_and_skips_checkpoint(
        self, test_engine: AsyncEngine
    ) -> None:
        async with _factory(test_engine)() as db:
            project = await _add_project(db, status="completed")
            pid = str(project.id)
            workflow = _FakeWorkflow(None)
            result = await _service(db, workflow).repair(_command(project))
            assert result.status == REPAIR_STATUS_REPAIRED
            assert result.needs_republish is True
            assert result.checkpoint_updated is False
            assert workflow.writes == []
            assert "## PT" not in await _slide_body(db, pid)

    async def test_partial_failure_retry_converges(
        self, test_engine: AsyncEngine
    ) -> None:
        # Scenario: the process dies between commits; the idempotent retry
        # converges both stores.
        async with _factory(test_engine)() as db:
            project = await _add_project(db)
            pid = str(project.id)
            state = {
                "localized_slides": [_scaffold_localized()],
                "presentation_validation": _blocking_report(),
                "presentation_policy_version": _V1,
            }
            workflow = _FakeWorkflow(state)
            workflow.fail_write = True
            with pytest.raises(RuntimeError):
                await _service(db, workflow).repair(_command(project))
            # Projection committed despite the checkpoint failure (drift).
            assert "## PT" not in await _slide_body(db, pid)
            assert workflow.writes == []
            # Retry with the fresh lock_version converges the checkpoint.
            await db.refresh(project)
            workflow.fail_write = False
            result = await _service(db, workflow).repair(_command(project))
            assert result.checkpoint_updated is True
            assert workflow.writes and workflow.state is not None

    async def test_audit_event_emitted(self, test_engine: AsyncEngine) -> None:
        async with _factory(test_engine)() as db:
            project = await _add_project(db)
            pid = str(project.id)
            state = {
                "localized_slides": [_scaffold_localized()],
                "presentation_validation": _blocking_report(),
                "presentation_policy_version": _V1,
            }
            from rag_backend.infrastructure.events.factory import get_event_publisher

            events = WorkflowEventService(get_event_publisher(None))
            await _service(db, _FakeWorkflow(state), events=events).repair(
                _command(project)
            )
            audit = await db.scalar(
                select(WorkflowAuditLogModel).where(
                    WorkflowAuditLogModel.aggregate_id == pid
                )
            )
            assert audit is not None
            assert audit.event_type == "carousel.repair.applied"

    async def test_lock_held_raises_mutation_in_progress(
        self, test_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Injected-lock double: another mutator holds the shared lock.
        @contextlib.asynccontextmanager
        async def _held_lock(*_args: object, **_kwargs: object) -> AsyncIterator[None]:
            raise CarouselConflictError(
                CarouselConflict.for_code(CONFLICT_CODE_MUTATION_IN_PROGRESS)
            )
            yield

        monkeypatch.setattr(
            carousel_repair_service, "carousel_project_lock", _held_lock
        )
        async with _factory(test_engine)() as db:
            project = await _add_project(db)
            pid = str(project.id)
            with pytest.raises(CarouselConflictError) as exc:
                await _service(db, _FakeWorkflow(None)).repair(_command(project))
            assert exc.value.conflict.code == CONFLICT_CODE_MUTATION_IN_PROGRESS
            assert "## PT" in await _slide_body(db, pid)
