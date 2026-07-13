"""Unit tests for the completed-project slide-edit service (AE-0314).

Gherkin: tests/features/carousel_text_edit_no_regen.feature

SQLite convention: the advisory lock no-ops on non-Postgres, so lock
serialization is exercised with an injected-lock double; the CAS, projection
commit, marker, and audit run against a real in-memory session. The checkpoint
convergence (source-of-truth option (a)) is exercised through a
``patch_parked_checkpoint`` double.
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

from rag_backend.application.services.carousel import carousel_slide_edit_service
from rag_backend.application.services.carousel.carousel_slide_edit_service import (
    CarouselSlideEditDeps,
    CarouselSlideEditService,
    SlideEditCommand,
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
from rag_backend.domain.constants.carousel_slide_edit import SLIDE_EDIT_STATUS_UPDATED
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_STATUS_APPROVED,
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
_IMAGE = "/renders/slide-1.png"
_SCAFFOLD_BODY = (
    "## PT\n**Heading:** x\n**Body:** raw scaffold leaked into the slide body "
    "which the parser never cleaned up before it reached the reviewer."
)
_CLEAN_HEADING = "Corrija o título agora"
_CLEAN_BODY = "Um corpo de slide limpo e curto que respeita o orçamento."


class _FakeWorkflow:
    """Checkpoint double: records patch_parked_checkpoint writes."""

    def __init__(self, *, parked: bool = True) -> None:
        self.parked = parked
        self.writes: list[dict[str, object]] = []

    async def patch_parked_checkpoint(
        self, project_id: str, values: dict[str, object]
    ) -> bool:
        self.writes.append(values)
        return self.parked


def _factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_rows(test_engine: AsyncEngine) -> AsyncIterator[None]:
    yield
    async with _factory(test_engine)() as db:
        await db.execute(delete(EventOutboxModel))
        await db.execute(delete(WorkflowAuditLogModel))
        await db.execute(delete(CarouselSlideModel))
        await db.execute(delete(CarouselProjectModel))
        await db.commit()


async def _add_completed_project(
    db: AsyncSession,
    *,
    phase_status: str = PHASE_STATUS_APPROVED,
    body: str = _CLEAN_BODY,
) -> CarouselProjectModel:
    project = CarouselProjectModel(
        id=str(uuid.uuid4()),
        topic="Edit",
        audience="Devs",
        niche="Tech",
        status="completed",
        current_phase="final_review",
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
            slide_number=1,
            slide_type="summary",
            heading="titulo antigo minusculo",
            body=body,
            image_path=_IMAGE,
            image_prompt="a neon skyline",
            extras={
                "summary_points": ["old point"],
                "translation_en": {"heading": "old heading", "body": "old body"},
            },
        )
    )
    await db.commit()
    return project


def _service(
    db: AsyncSession,
    workflow: _FakeWorkflow,
    *,
    events: WorkflowEventService | None = None,
) -> CarouselSlideEditService:
    return CarouselSlideEditService(
        CarouselSlideEditDeps(
            db=db,
            workflow_service=cast(EditorialWorkflowService, workflow),
            repo=PostgresCarouselRepository(db),
            events=events,
        )
    )


def _edit_payload(
    *,
    heading: str = _CLEAN_HEADING,
    body: str = _CLEAN_BODY,
    summary_points: list[str] | None = None,
) -> dict[str, object]:
    pt: dict[str, object] = {"slide_type": "summary", "heading": heading, "body": body}
    if summary_points is not None:
        pt["summary_points"] = summary_points
    return {
        "slide_index": 1,
        "slide_type": "summary",
        "presentation_pt": pt,
        "presentation_en": {"slide_type": "summary", "heading": "New", "body": "Body."},
    }


def _command(
    project: CarouselProjectModel,
    edited: list[dict[str, object]],
    *,
    lock_version: int | None = None,
) -> SlideEditCommand:
    return SlideEditCommand(
        project_id=str(project.id),
        phase_status=str(project.phase_status or ""),
        lock_version=lock_version if lock_version is not None else 1,
        policy_version=_V1,
        actor_user_id="user-1",
        edited_slides=edited,
    )


async def _slide(db: AsyncSession, project_id: str) -> CarouselSlideModel:
    row = await db.scalar(
        select(CarouselSlideModel).where(CarouselSlideModel.project_id == project_id)
    )
    assert row is not None
    return row


@pytest.mark.asyncio
class TestSlideEditService:
    async def test_edit_persists_copy_marks_republish_and_keeps_image(
        self, test_engine: AsyncEngine
    ) -> None:
        # Scenario: fix casing on a completed carousel; images unchanged.
        async with _factory(test_engine)() as db:
            project = await _add_completed_project(db)
            pid = str(project.id)
            workflow = _FakeWorkflow(parked=True)
            result = await _service(db, workflow).edit(
                _command(project, [_edit_payload()])
            )
            assert result.status == SLIDE_EDIT_STATUS_UPDATED
            assert result.needs_republish is True
            assert result.checkpoint_updated is True
            assert result.updated_slides == (1,)
            slide = await _slide(db, pid)
            assert slide.heading == _CLEAN_HEADING
            # Image assets are never touched by a text edit (AC).
            assert slide.image_path == _IMAGE
            assert slide.image_prompt == "a neon skyline"
            await db.refresh(project)
            assert project.needs_republish_since is not None

    async def test_checkpoint_written_with_fresh_report_option_a(
        self, test_engine: AsyncEngine
    ) -> None:
        # AC #5: post-edit validation reflects the edited copy (no stale report).
        async with _factory(test_engine)() as db:
            project = await _add_completed_project(db, body=_SCAFFOLD_BODY)
            workflow = _FakeWorkflow(parked=True)
            result = await _service(db, workflow).edit(
                _command(project, [_edit_payload()])
            )
            assert result.report["blocking"] is False
            # Option (a): the edited copy + fresh report went to the checkpoint.
            assert workflow.writes
            written = workflow.writes[0]
            assert "localized_slides" in written
            assert written["presentation_validation"]["blocking"] is False

    async def test_legacy_end_thread_skips_checkpoint(
        self, test_engine: AsyncEngine
    ) -> None:
        # Fallback: a non-parked (legacy END) thread persists projection only.
        async with _factory(test_engine)() as db:
            project = await _add_completed_project(db)
            workflow = _FakeWorkflow(parked=False)
            result = await _service(db, workflow).edit(
                _command(project, [_edit_payload()])
            )
            assert result.needs_republish is True
            assert result.checkpoint_updated is False

    async def test_summary_extras_are_edited(self, test_engine: AsyncEngine) -> None:
        # AC: editing a summary slide edits its structured extras.
        async with _factory(test_engine)() as db:
            project = await _add_completed_project(db)
            pid = str(project.id)
            edited = [_edit_payload(summary_points=["fresh point one", "fresh two"])]
            await _service(db, _FakeWorkflow()).edit(_command(project, edited))
            slide = await _slide(db, pid)
            extras = slide.extras or {}
            assert extras.get("summary_points") == ["fresh point one", "fresh two"]

    async def test_run_in_progress_rejected(self, test_engine: AsyncEngine) -> None:
        async with _factory(test_engine)() as db:
            project = await _add_completed_project(
                db, phase_status=PHASE_STATUS_IN_PROGRESS
            )
            with pytest.raises(CarouselConflictError) as exc:
                await _service(db, _FakeWorkflow()).edit(
                    _command(project, [_edit_payload()])
                )
            assert exc.value.conflict.code == CONFLICT_CODE_RUN_IN_PROGRESS

    async def test_stale_cas_loses(self, test_engine: AsyncEngine) -> None:
        async with _factory(test_engine)() as db:
            project = await _add_completed_project(db)
            pid = str(project.id)
            with pytest.raises(CarouselConflictError) as exc:
                await _service(db, _FakeWorkflow()).edit(
                    _command(project, [_edit_payload()], lock_version=999)
                )
            assert exc.value.conflict.code == CONFLICT_CODE_VERSION_CONFLICT
            await db.rollback()
            slide = await _slide(db, pid)
            assert slide.heading == "titulo antigo minusculo"

    async def test_lock_held_raises_mutation_in_progress(
        self, test_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Injected-lock double: a concurrent repair/republish holds the lock.
        @contextlib.asynccontextmanager
        async def _held_lock(*_a: object, **_k: object) -> AsyncIterator[None]:
            raise CarouselConflictError(
                CarouselConflict.for_code(CONFLICT_CODE_MUTATION_IN_PROGRESS)
            )
            yield

        monkeypatch.setattr(
            carousel_slide_edit_service, "carousel_project_lock", _held_lock
        )
        async with _factory(test_engine)() as db:
            project = await _add_completed_project(db)
            pid = str(project.id)
            with pytest.raises(CarouselConflictError) as exc:
                await _service(db, _FakeWorkflow()).edit(
                    _command(project, [_edit_payload()])
                )
            assert exc.value.conflict.code == CONFLICT_CODE_MUTATION_IN_PROGRESS
            slide = await _slide(db, pid)
            assert slide.heading == "titulo antigo minusculo"

    async def test_audit_event_emitted(self, test_engine: AsyncEngine) -> None:
        async with _factory(test_engine)() as db:
            project = await _add_completed_project(db)
            pid = str(project.id)
            from rag_backend.infrastructure.events.factory import get_event_publisher

            events = WorkflowEventService(get_event_publisher(None))
            await _service(db, _FakeWorkflow(), events=events).edit(
                _command(project, [_edit_payload()])
            )
            audit = await db.scalar(
                select(WorkflowAuditLogModel).where(
                    WorkflowAuditLogModel.aggregate_id == pid
                )
            )
            assert audit is not None
            assert audit.event_type == "carousel.slide.edited"
