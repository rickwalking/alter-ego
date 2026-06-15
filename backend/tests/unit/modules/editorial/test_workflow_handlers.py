"""Unit tests for the editorial workflow handlers (AE-0110).

These cover the AE-0110 acceptance criteria at the handler boundary — the
use-case layer the thin workflow routes delegate to:

* **Engine wrapping** — the handlers WRAP the injected workflow engine (they
  never reconstruct it) and pass the bound request session to it through the ACL,
  so the LangGraph checkpoint key (``thread_id == project_id``) and the
  ``CarouselWorkflowState`` schema flow through unchanged;
* **Read overlay via the ACL** — ``get_state`` / ``start`` surface the row's
  ``phase_progress`` + ``lock_version`` read THROUGH the ACL (the single ORM
  seam), never by touching the carousel ORM in the handler/route;
* **Single commit owner** — ``start`` / ``mark_resume_in_progress`` commit the
  workflow-owned writes ONCE via the ACL (the platform UoW single committer); the
  handler never calls ``db.commit()`` and a fake engine that stages a WO change
  is proven persisted only after the handler's commit;
* **404 + error mapping** — ``get_state`` returns ``None`` when the engine has no
  checkpoint (route maps 404) and a ``ValueError`` from the engine propagates
  (route maps 400).

External clients are never constructed; the tests use an in-memory SQLite session
and a fake engine — no API keys required (CI-safe). Gherkin not applicable per
the ticket (behavior-preserving extraction; the API+SSE contract is locked by the
AE-0106 safety net).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.application.services.carousel.editorial_workflow_types import (
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.editorial.application.workflow_handlers import (
    EditorialWorkflowHandlers,
    StartWorkflowCommand,
    WorkflowStateView,
)
from rag_backend.modules.editorial.infrastructure.carousel_project_write_owner import (
    CarouselProjectWriteOwner,
)
from rag_backend.modules.editorial.infrastructure.legacy_carousel_acl import (
    LegacyCarouselAcl,
)

_TOPIC = "AI agents"
_AUDIENCE = "Developers"
_NICHE = "Tech"
_PHASE_PROGRESS: dict[str, str | int | list[dict[str, str | int]]] = {
    "percent": 42,
    "step": "drafting",
}


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """In-memory SQLite session with the carousel schema created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        yield db
    db_config.c_engine = None
    await engine.dispose()


async def _seed_project(
    session: AsyncSession,
    *,
    lock_version: int = 1,
    phase_status: str = PHASE_STATUS_AWAITING_HUMAN,
) -> str:
    """Persist a carousel row and return its id (== checkpoint thread_id)."""
    project_id = str(uuid.uuid4())
    model = CarouselProjectModel(
        id=project_id,
        topic=_TOPIC,
        audience=_AUDIENCE,
        niche=_NICHE,
        current_phase=PHASE_CONTENT,
        phase_status=phase_status,
        lock_version=lock_version,
        phase_progress=dict(_PHASE_PROGRESS),
    )
    session.add(model)
    await session.commit()
    return project_id


def _state(project_id: str) -> CarouselWorkflowState:
    return {
        "project_id": project_id,
        "current_phase": PHASE_CONTENT,
        "phase_status": PHASE_STATUS_AWAITING_HUMAN,
    }


def _handlers(session: AsyncSession) -> EditorialWorkflowHandlers:
    acl = LegacyCarouselAcl(session, CarouselProjectWriteOwner(session))
    return EditorialWorkflowHandlers(acl=acl)


class _FakeEngine:
    """Deterministic workflow engine recording the session it was bound to.

    Mirrors the methods the routes call on ``EditorialWorkflowService``. It
    records the ``db`` passed by the ACL (proving the handler binds the request
    session) and can stage a workflow-owned write via the AE-0107 owner so the
    single-commit contract is observable.
    """

    def __init__(self, project_id: str, *, has_state: bool) -> None:
        self._project_id = project_id
        self._has_state = has_state
        self.received_db: object | None = None
        self.start_calls = 0

    async def get_workflow_state(
        self,
        project_id: str,
        db: object | None = None,
    ) -> CarouselWorkflowState | None:
        self.received_db = db
        if not self._has_state or project_id != self._project_id:
            return None
        return _state(project_id)

    async def start_workflow(
        self,
        project_id: str,
        workflow_input: EditorialWorkflowStartInput,
        db: object | None = None,
    ) -> CarouselWorkflowState:
        del workflow_input
        self.received_db = db
        self.start_calls += 1
        # Stage a workflow-owned write (flush only) to prove the handler commits.
        if isinstance(db, AsyncSession):
            await CarouselProjectWriteOwner(db).assign_reviewer(
                project_id, "reviewer-xyz"
            )
        return _state(project_id)

    async def mark_resume_in_progress(
        self,
        project_id: str,
        db: object | None = None,
    ) -> str:
        self.received_db = db
        if isinstance(db, AsyncSession):
            await CarouselProjectWriteOwner(db).sync_phase(
                project_id,
                {**_state(project_id), "phase_status": PHASE_STATUS_IN_PROGRESS},
            )
        return PHASE_CONTENT

    def stream_phase_updates(
        self,
        project_id: str,
        *,
        phase_progress: dict[str, object] | None = None,
    ) -> AsyncIterator[dict[str, object]]:
        return _fixed_events(project_id, phase_progress)


async def _fixed_events(
    project_id: str,
    phase_progress: dict[str, object] | None,
) -> AsyncIterator[dict[str, object]]:
    yield {"event": "phase_change", "project_id": project_id}
    yield {"event": "progress", "phase_progress": phase_progress}


class TestGetState:
    """get_state: engine wrapping + ACL read overlay + 404 mapping."""

    @pytest.mark.asyncio
    async def test_returns_state_with_row_overlay(self, session: AsyncSession) -> None:
        project_id = await _seed_project(session, lock_version=2)
        engine = _FakeEngine(project_id, has_state=True)
        view = await _handlers(session).get_state(engine, project_id)
        assert isinstance(view, WorkflowStateView)
        assert view.state["current_phase"] == PHASE_CONTENT
        # phase_progress + lock_version read THROUGH the ACL (no ORM in handler).
        assert view.phase_progress == dict(_PHASE_PROGRESS)
        assert view.lock_version == 2
        # The handler bound the request session to the engine (in_progress merge).
        assert engine.received_db is session

    @pytest.mark.asyncio
    async def test_returns_none_when_no_checkpoint(self, session: AsyncSession) -> None:
        project_id = await _seed_project(session)
        engine = _FakeEngine(project_id, has_state=False)
        view = await _handlers(session).get_state(engine, project_id)
        assert view is None


class TestStart:
    """start: engine wrapping + single commit + post-commit reload overlay."""

    @pytest.mark.asyncio
    async def test_commits_staged_write_and_overlays_metadata(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session, lock_version=1)
        engine = _FakeEngine(project_id, has_state=False)
        view = await _handlers(session).start(
            engine,
            StartWorkflowCommand(
                project_id=project_id,
                workflow_input=EditorialWorkflowStartInput(
                    topic=_TOPIC, audience=_AUDIENCE, brief="", sources=[]
                ),
            ),
        )
        assert engine.start_calls == 1
        assert engine.received_db is session
        assert view.phase_progress == dict(_PHASE_PROGRESS)
        assert view.lock_version == 1
        # The engine staged assign_reviewer; the handler's single commit persisted
        # it. Read it back on a FRESH session to prove the commit (not just flush).
        factory = async_sessionmaker(session.bind, expire_on_commit=False)
        async with factory() as fresh:
            persisted = await fresh.get(CarouselProjectModel, project_id)
            assert persisted is not None
            assert persisted.assigned_reviewer_id == "reviewer-xyz"

    @pytest.mark.asyncio
    async def test_value_error_propagates(self, session: AsyncSession) -> None:
        project_id = await _seed_project(session)

        class _RaisingEngine(_FakeEngine):
            async def start_workflow(
                self,
                project_id: str,
                workflow_input: EditorialWorkflowStartInput,
                db: object | None = None,
            ) -> CarouselWorkflowState:
                raise ValueError("bad input")

        with pytest.raises(ValueError, match="bad input"):
            await _handlers(session).start(
                _RaisingEngine(project_id, has_state=False),
                StartWorkflowCommand(
                    project_id=project_id,
                    workflow_input=EditorialWorkflowStartInput(
                        topic=_TOPIC, audience=_AUDIENCE, brief="", sources=[]
                    ),
                ),
            )


class TestMarkResumeInProgress:
    """mark_resume_in_progress: engine wrapping + single commit."""

    @pytest.mark.asyncio
    async def test_commits_phase_status_and_returns_phase(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session)
        engine = _FakeEngine(project_id, has_state=True)
        phase = await _handlers(session).mark_resume_in_progress(engine, project_id)
        assert phase == PHASE_CONTENT
        assert engine.received_db is session
        factory = async_sessionmaker(session.bind, expire_on_commit=False)
        async with factory() as fresh:
            persisted = await fresh.get(CarouselProjectModel, project_id)
            assert persisted is not None
            assert persisted.phase_status == PHASE_STATUS_IN_PROGRESS


class TestStreamPhaseUpdates:
    """stream_phase_updates: pure engine pass-through (no DB writes)."""

    @pytest.mark.asyncio
    async def test_passes_through_engine_events(self, session: AsyncSession) -> None:
        project_id = await _seed_project(session)
        engine = _FakeEngine(project_id, has_state=True)
        events = [
            event
            async for event in EditorialWorkflowHandlers.stream_phase_updates(
                engine, project_id, phase_progress={"percent": 10}
            )
        ]
        assert [event["event"] for event in events] == ["phase_change", "progress"]
        assert events[1]["phase_progress"] == {"percent": 10}


class TestEditorialWorkflowHandlerProviderGuard:
    """The edge provider rejects a module bootstrapped without the carousel ACL.

    Covers the ``acl is None`` guard in ``get_editorial_workflow_handlers`` so the
    branch is exercised by tests (no ``# pragma: no cover``).
    """

    def test_raises_runtime_error_when_acl_missing(self) -> None:
        from unittest.mock import MagicMock

        from rag_backend.api.dependencies.editorial import (
            _ERR_MODULE_WITHOUT_ACL,
            get_editorial_workflow_handlers,
        )
        from rag_backend.modules.editorial.bootstrap import EditorialModule

        module = EditorialModule(
            service=MagicMock(),
            unit_of_work=MagicMock(),
            legacy_carousel_acl=None,
        )
        with pytest.raises(RuntimeError, match=_ERR_MODULE_WITHOUT_ACL):
            get_editorial_workflow_handlers(module=module)
