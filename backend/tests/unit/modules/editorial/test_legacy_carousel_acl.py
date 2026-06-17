"""Contract/adapter tests for the legacy carousel ACL (AE-0109).

These cover the AE-0109 acceptance criteria at the adapter boundary:

* **Mapping round-trip** — a legacy ``CarouselProjectModel`` translates into the
  editorial aggregate (``EditorialProject`` + ``EditorialWorkflow``) with the
  workflow-owned fields mapped (``current_phase`` -> ``phase``, ``phase_status``,
  ``workflow_status``) and the canonical ``CarouselProject`` entity surfaced;
* **Write delegation** — every workflow-owned write goes THROUGH the AE-0107
  ``CarouselProjectWriteOwner`` (the ACL never mutates the ORM row itself); the
  delegation is proven by the resulting persisted DB state;
* **Concurrency + checkpoint identity preserved** — the ``lock_version`` token is
  surfaced verbatim and the resume CAS bump (delegated to the owner) preserves the
  optimistic-lock expected-version contract; the LangGraph checkpoint
  ``thread_id`` equals the project id, unchanged.

Behavior-preserving adapter; verified here + by the AE-0106 safety net (Gherkin
not applicable per the ticket). External clients are never constructed; the tests
use an in-memory SQLite session — no API keys required.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_IN_PROGRESS,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.models import CarouselProject, CarouselStatus
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.editorial.domain.models import (
    EditorialProject,
    EditorialWorkflow,
)
from rag_backend.modules.editorial.infrastructure.carousel_project_write_owner import (
    CarouselProjectWriteOwner,
)
from rag_backend.modules.editorial.infrastructure.legacy_carousel_acl import (
    EditorialProjectView,
    LegacyCarouselAcl,
)

_TOPIC = "AI agents"
_AUDIENCE = "Developers"
_NICHE = "Tech"
_REVIEWER_ID = "reviewer-123"
_CAPTION = "Synced caption"
_BLOG = "# Synced blog"


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
    current_phase: str = PHASE_CONTENT,
    phase_status: str = PHASE_STATUS_AWAITING_HUMAN,
    workflow_status: str = "",
) -> str:
    """Persist a carousel row and return its id (== checkpoint thread_id)."""
    project_id = str(uuid.uuid4())
    model = CarouselProjectModel(
        id=project_id,
        topic=_TOPIC,
        audience=_AUDIENCE,
        niche=_NICHE,
        current_phase=current_phase,
        phase_status=phase_status,
        workflow_status=workflow_status,
        lock_version=lock_version,
    )
    session.add(model)
    await session.commit()
    return project_id


def _acl(session: AsyncSession) -> LegacyCarouselAcl:
    """Build the ACL over a real AE-0107 write owner (no model mutation here)."""
    return LegacyCarouselAcl(session, CarouselProjectWriteOwner(session))


class TestReadSideMapping:
    """Scenario: a legacy row maps to the editorial aggregate."""

    @pytest.mark.asyncio
    async def test_to_editorial_maps_workflow_owned_fields(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(
            session,
            current_phase=PHASE_DESIGN,
            phase_status=PHASE_STATUS_IN_PROGRESS,
            workflow_status=WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
            lock_version=3,
        )
        view = await _acl(session).load_editorial(project_id)

        assert view is not None
        assert isinstance(view, EditorialProjectView)
        assert isinstance(view.project, EditorialProject)
        assert isinstance(view.project.workflow, EditorialWorkflow)
        # workflow-owned fields mapped (current_phase -> phase).
        assert view.project.workflow.phase == PHASE_DESIGN
        assert view.project.workflow.phase_status == PHASE_STATUS_IN_PROGRESS
        assert view.project.workflow.workflow_status == (
            WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
        )

    @pytest.mark.asyncio
    async def test_to_editorial_surfaces_canonical_carousel_entity(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session)
        view = await _acl(session).load_editorial(project_id)

        assert view is not None
        carousel = view.project.project
        assert isinstance(carousel, CarouselProject)
        assert carousel.topic == _TOPIC
        assert carousel.audience == _AUDIENCE
        assert carousel.niche == _NICHE
        assert carousel.status == CarouselStatus.PENDING
        assert str(carousel.id) == project_id

    @pytest.mark.asyncio
    async def test_load_editorial_returns_none_when_absent(
        self, session: AsyncSession
    ) -> None:
        view = await _acl(session).load_editorial(str(uuid.uuid4()))
        assert view is None


class TestCheckpointAndLockPreserved:
    """Scenario: lock_version + checkpoint thread_id are preserved exactly."""

    @pytest.mark.asyncio
    async def test_lock_version_surfaced_verbatim(self, session: AsyncSession) -> None:
        project_id = await _seed_project(session, lock_version=7)
        view = await _acl(session).load_editorial(project_id)

        assert view is not None
        assert view.lock_version == 7

    @pytest.mark.asyncio
    async def test_checkpoint_thread_id_equals_project_id(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session)
        view = await _acl(session).load_editorial(project_id)

        assert view is not None
        # LangGraph checkpoint identifier: thread_id == project_id, unchanged.
        assert view.checkpoint_thread_id == project_id
        assert view.checkpoint_thread_id == str(view.project.project.id)


class TestWriteDelegation:
    """Scenario: every workflow-owned write goes THROUGH the AE-0107 owner."""

    @pytest.mark.asyncio
    async def test_assign_reviewer_persists_via_owner(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session)
        acl = _acl(session)

        await acl.assign_reviewer(project_id, _REVIEWER_ID)
        await acl.commit()

        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        assert model.assigned_reviewer_id == _REVIEWER_ID

    @pytest.mark.asyncio
    async def test_sync_workflow_persists_phase_columns_via_owner(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session)
        acl = _acl(session)
        state: CarouselWorkflowState = {
            "current_phase": PHASE_DESIGN,
            "phase_status": PHASE_STATUS_IN_PROGRESS,
            "workflow_status": WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
            "caption": _CAPTION,
            "blog_markdown": _BLOG,
        }

        await acl.sync_workflow(project_id, state)
        await acl.commit()

        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        assert model.current_phase == PHASE_DESIGN
        assert model.phase_status == PHASE_STATUS_IN_PROGRESS
        assert model.workflow_status == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
        # AE-0204: caption is NOT synced onto the embedded column anymore — it has a
        # canonical home (blog_posts.distribution); the checkpoint sync is decoupled.
        # ``caption`` stays in ``state`` to prove the sync intentionally ignores it.
        assert model.caption is None
        # blog_markdown remains synced (AE-0163's domain).
        assert model.blog_markdown == _BLOG

    @pytest.mark.asyncio
    async def test_sync_workflow_failed_phase_marks_status_failed(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session)
        acl = _acl(session)
        state: CarouselWorkflowState = {
            "current_phase": PHASE_DESIGN,
            "phase_status": PHASE_STATUS_FAILED,
        }

        await acl.sync_workflow(project_id, state)
        await acl.commit()

        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        # The owner's byte-identical sync sets status=FAILED on a failed phase.
        assert model.status == CarouselStatus.FAILED.value

    @pytest.mark.asyncio
    async def test_set_phase_status_and_commit_persists_via_owner(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(
            session, phase_status=PHASE_STATUS_AWAITING_HUMAN
        )
        acl = _acl(session)

        await acl.set_phase_status_and_commit(project_id, PHASE_STATUS_IN_PROGRESS)

        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        assert model.phase_status == PHASE_STATUS_IN_PROGRESS


class TestLockVersionBumpDelegation:
    """Scenario: the resume lock_version CAS is delegated, semantics intact."""

    @pytest.mark.asyncio
    async def test_bump_resume_lock_version_advances_token(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session, lock_version=1)
        acl = _acl(session)

        new_version = await acl.bump_resume_lock_version(project_id, expected_version=1)
        await acl.commit()

        assert new_version == 2
        view = await acl.load_editorial(project_id)
        assert view is not None
        assert view.lock_version == 2

    @pytest.mark.asyncio
    async def test_bump_resume_lock_version_rejects_stale_expected_version(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session, lock_version=1)
        acl = _acl(session)

        # The CAS expected-version contract is preserved: a stale version raises.
        with pytest.raises(ValueError, match=ERR_VERSION_CONFLICT):
            await acl.bump_resume_lock_version(project_id, expected_version=99)
