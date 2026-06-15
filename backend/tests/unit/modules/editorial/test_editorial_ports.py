"""Unit tests for the editorial ports + adapters and the approval/release split.

These cover the AE-0111 acceptance criteria at the port/adapter boundary:

* **Source / assignments / review / locking behind ports** — each of the four
  editorial ports is satisfied by an adapter that DELEGATES to the existing
  infrastructure (the workflow engine or the AE-0109 ACL → AE-0107 owner); the
  editorial application service depends only on the port Protocols.
* **Approval != public release (contract split)** — approval (``workflow_status
  -> approved_for_publish``) and public release (``is_public``) are DISTINCT
  states, proven independent across all four combinations.
* **``lock_version`` preserved** — the optimistic-locking port forwards the
  resume CAS unchanged (advances the token; rejects a stale expected version),
  delegating to the byte-identical ``OptimisticLockService``.
* **Review-action behavior preserved** — the review-decision port forwards the
  reviewer decision to the engine's unchanged resume path.

External clients are never constructed; the ACL-backed tests use an in-memory
SQLite session and the engine-backed tests use fakes — no API keys required
(CI-safe). Gherkin not applicable per the ticket (behavior-preserving
extraction; the API+SSE contract is locked by the AE-0106 safety net).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.application.services.carousel.editorial_workflow_types import (
    ResumeWorkflowInput,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_STATUS_AWAITING_HUMAN,
    REVIEW_ACTION_APPROVE,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.editorial.application.service import (
    EditorialPorts,
    EditorialService,
)
from rag_backend.modules.editorial.domain.ports import (
    ApprovalPort,
    CarouselRepository,
    OptimisticLockingPort,
    PublicReleasePort,
    ReviewDecisionPort,
    ReviewerAssignmentPort,
    SourceMaterialPort,
)
from rag_backend.modules.editorial.domain.release import (
    ApprovalState,
    PublicReleaseState,
)
from rag_backend.modules.editorial.infrastructure.carousel_project_write_owner import (
    CarouselProjectWriteOwner,
)
from rag_backend.modules.editorial.infrastructure.editorial_port_adapters import (
    AclApprovalAdapter,
    AclOptimisticLockingAdapter,
    AclPublicReleaseAdapter,
    AclReviewerAssignmentAdapter,
    EngineReviewDecisionAdapter,
    EngineSourceMaterialAdapter,
)
from rag_backend.modules.editorial.infrastructure.legacy_carousel_acl import (
    LegacyCarouselAcl,
)

_TOPIC = "AI agents"
_AUDIENCE = "Developers"
_NICHE = "Tech"
_REVIEWER_ID = "reviewer-123"
_SOURCES = [{"url": "https://example.com", "text": "source body"}]
_FINDINGS = {"summary": "synthesized"}


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
    workflow_status: str = "",
    is_public: bool = False,
) -> str:
    """Persist a carousel row and return its id (== checkpoint thread_id)."""
    project_id = str(uuid.uuid4())
    model = CarouselProjectModel(
        id=project_id,
        topic=_TOPIC,
        audience=_AUDIENCE,
        niche=_NICHE,
        current_phase=PHASE_CONTENT,
        phase_status=PHASE_STATUS_AWAITING_HUMAN,
        workflow_status=workflow_status,
        is_public=is_public,
        lock_version=lock_version,
    )
    session.add(model)
    await session.commit()
    return project_id


def _acl(session: AsyncSession) -> LegacyCarouselAcl:
    return LegacyCarouselAcl(session, CarouselProjectWriteOwner(session))


class _FakeSourceEngine:
    """Records the sources it was asked to synthesize and returns fixed findings."""

    def __init__(self) -> None:
        self.received: list[dict[str, str]] | None = None

    async def synthesize_research(self, sources: list[dict[str, str]]) -> object:
        self.received = sources
        return _FINDINGS


class _FakeReviewEngine:
    """Records the resume input it received and returns a fixed state."""

    def __init__(self) -> None:
        self.received: ResumeWorkflowInput | None = None

    async def resume_workflow(
        self,
        params: ResumeWorkflowInput,
    ) -> CarouselWorkflowState:
        self.received = params
        return {"project_id": params.project_id, "current_phase": PHASE_CONTENT}


class TestAdaptersImplementPorts:
    """Each adapter structurally satisfies its port Protocol."""

    def test_adapters_are_runtime_instances_of_their_ports(
        self, session: AsyncSession
    ) -> None:
        acl = _acl(session)
        assert isinstance(
            EngineSourceMaterialAdapter(_FakeSourceEngine()), SourceMaterialPort
        )
        assert isinstance(
            EngineReviewDecisionAdapter(_FakeReviewEngine()), ReviewDecisionPort
        )
        assert isinstance(AclReviewerAssignmentAdapter(acl), ReviewerAssignmentPort)
        assert isinstance(AclOptimisticLockingAdapter(acl), OptimisticLockingPort)
        assert isinstance(AclApprovalAdapter(acl), ApprovalPort)
        assert isinstance(AclPublicReleaseAdapter(acl), PublicReleasePort)


class TestSourceMaterialPort:
    """source material is accessed via the port (delegates to the engine)."""

    @pytest.mark.asyncio
    async def test_synthesize_delegates_to_engine(self) -> None:
        engine = _FakeSourceEngine()
        adapter = EngineSourceMaterialAdapter(engine)
        result = await adapter.synthesize(_SOURCES)
        assert result == _FINDINGS
        assert engine.received == _SOURCES


class TestReviewDecisionPort:
    """review decisions are recorded via the port (delegates to engine resume)."""

    @pytest.mark.asyncio
    async def test_record_decision_delegates_to_engine_resume(self) -> None:
        engine = _FakeReviewEngine()
        adapter = EngineReviewDecisionAdapter(engine)
        decision = ResumeWorkflowInput(
            project_id="p1",
            action=REVIEW_ACTION_APPROVE,
            reviewer_id=_REVIEWER_ID,
        )
        state = await adapter.record_decision(decision)
        assert engine.received is decision
        assert isinstance(state, dict)
        assert state["current_phase"] == PHASE_CONTENT

    @pytest.mark.asyncio
    async def test_record_decision_rejects_wrong_type(self) -> None:
        adapter = EngineReviewDecisionAdapter(_FakeReviewEngine())
        with pytest.raises(TypeError):
            await adapter.record_decision({"action": "approve"})


class TestReviewerAssignmentPort:
    """assignments are written via the port (delegates to the ACL → owner)."""

    @pytest.mark.asyncio
    async def test_assign_reviewer_persists_via_owner(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session)
        acl = _acl(session)
        await AclReviewerAssignmentAdapter(acl).assign_reviewer(
            project_id, _REVIEWER_ID
        )
        await acl.commit()
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        assert model.assigned_reviewer_id == _REVIEWER_ID


class TestOptimisticLockingPort:
    """lock_version CAS is run via the port; semantics preserved exactly."""

    @pytest.mark.asyncio
    async def test_bump_advances_token(self, session: AsyncSession) -> None:
        project_id = await _seed_project(session, lock_version=1)
        acl = _acl(session)
        new_version = await AclOptimisticLockingAdapter(acl).bump_resume_lock_version(
            project_id, expected_version=1
        )
        await acl.commit()
        assert new_version == 2

    @pytest.mark.asyncio
    async def test_bump_rejects_stale_expected_version(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session, lock_version=1)
        acl = _acl(session)
        with pytest.raises(ValueError, match=ERR_VERSION_CONFLICT):
            await AclOptimisticLockingAdapter(acl).bump_resume_lock_version(
                project_id, expected_version=99
            )


class TestApprovalReleaseSplit:
    """approval (workflow_status) != public release (is_public): four combos."""

    @pytest.mark.asyncio
    async def test_approved_not_public(self, session: AsyncSession) -> None:
        project_id = await _seed_project(
            session,
            workflow_status=WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
            is_public=False,
        )
        acl = _acl(session)
        approval = await AclApprovalAdapter(acl).get_approval_state(project_id)
        release = await AclPublicReleaseAdapter(acl).get_release_state(project_id)
        assert approval is not None and approval.is_approved is True
        assert release is not None and release.is_public is False

    @pytest.mark.asyncio
    async def test_public_not_approved(self, session: AsyncSession) -> None:
        project_id = await _seed_project(session, workflow_status="", is_public=True)
        acl = _acl(session)
        approval = await AclApprovalAdapter(acl).get_approval_state(project_id)
        release = await AclPublicReleaseAdapter(acl).get_release_state(project_id)
        assert approval is not None and approval.is_approved is False
        assert release is not None and release.is_public is True

    @pytest.mark.asyncio
    async def test_approved_and_public(self, session: AsyncSession) -> None:
        project_id = await _seed_project(
            session,
            workflow_status=WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
            is_public=True,
        )
        acl = _acl(session)
        approval = await AclApprovalAdapter(acl).get_approval_state(project_id)
        release = await AclPublicReleaseAdapter(acl).get_release_state(project_id)
        assert approval is not None and approval.is_approved is True
        assert release is not None and release.is_public is True

    @pytest.mark.asyncio
    async def test_neither_approved_nor_public(self, session: AsyncSession) -> None:
        project_id = await _seed_project(session, workflow_status="", is_public=False)
        acl = _acl(session)
        approval = await AclApprovalAdapter(acl).get_approval_state(project_id)
        release = await AclPublicReleaseAdapter(acl).get_release_state(project_id)
        assert approval is not None and approval.is_approved is False
        assert release is not None and release.is_public is False

    @pytest.mark.asyncio
    async def test_returns_none_when_absent(self, session: AsyncSession) -> None:
        missing = str(uuid.uuid4())
        acl = _acl(session)
        assert await AclApprovalAdapter(acl).get_approval_state(missing) is None
        assert await AclPublicReleaseAdapter(acl).get_release_state(missing) is None


class TestApprovalReleaseStateValueObjects:
    """The domain value objects keep approval and release independent."""

    def test_approval_state_builder_and_predicate(self) -> None:
        approved = ApprovalState.from_workflow_status(
            WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
        )
        assert approved.is_approved is True
        assert ApprovalState.from_workflow_status(None).is_approved is False
        assert ApprovalState.from_workflow_status("draft").is_approved is False

    def test_public_release_state_builder(self) -> None:
        assert PublicReleaseState.from_is_public(is_public=True).is_public is True
        assert PublicReleaseState.from_is_public(is_public=False).is_public is False


class TestEditorialServicePortWiring:
    """The application service forwards to the injected ports only."""

    @pytest.mark.asyncio
    async def test_service_forwards_each_use_case_to_its_port(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(
            session,
            lock_version=1,
            workflow_status=WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
            is_public=True,
        )
        acl = _acl(session)
        source_engine = _FakeSourceEngine()
        review_engine = _FakeReviewEngine()
        service = EditorialService(
            repository=AsyncMock(spec=CarouselRepository),
            ports=EditorialPorts(
                source_material=EngineSourceMaterialAdapter(source_engine),
                reviewer_assignment=AclReviewerAssignmentAdapter(acl),
                review_decision=EngineReviewDecisionAdapter(review_engine),
                optimistic_locking=AclOptimisticLockingAdapter(acl),
                approval=AclApprovalAdapter(acl),
                public_release=AclPublicReleaseAdapter(acl),
            ),
        )

        assert await service.synthesize_sources(_SOURCES) == _FINDINGS
        await service.assign_reviewer(project_id, _REVIEWER_ID)
        decision = ResumeWorkflowInput(
            project_id=project_id,
            action=REVIEW_ACTION_APPROVE,
            reviewer_id=_REVIEWER_ID,
        )
        state = await service.record_review_decision(decision)
        assert isinstance(state, dict)
        new_version = await service.bump_resume_lock_version(project_id, 1)
        await acl.commit()
        assert new_version == 2

        approval = await service.get_approval_state(project_id)
        release = await service.get_release_state(project_id)
        assert approval is not None and approval.is_approved is True
        assert release is not None and release.is_public is True
        # The assignment was forwarded to the ACL → owner (persisted).
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        assert model.assigned_reviewer_id == _REVIEWER_ID

    @pytest.mark.asyncio
    async def test_each_use_case_raises_when_its_port_missing(self) -> None:
        service = EditorialService(repository=AsyncMock(spec=CarouselRepository))
        with pytest.raises(RuntimeError, match="source_material"):
            await service.synthesize_sources(_SOURCES)
        with pytest.raises(RuntimeError, match="reviewer_assignment"):
            await service.assign_reviewer("p", "r")
        with pytest.raises(RuntimeError, match="review_decision"):
            await service.record_review_decision(
                ResumeWorkflowInput(project_id="p", action="approve", reviewer_id="r")
            )
        with pytest.raises(RuntimeError, match="optimistic_locking"):
            await service.bump_resume_lock_version("p", 1)
        with pytest.raises(RuntimeError, match="approval"):
            await service.get_approval_state("p")
        with pytest.raises(RuntimeError, match="public_release"):
            await service.get_release_state("p")


class TestBootstrapWiresAclPorts:
    """bootstrap wires the ACL-backed ports when an ACL is supplied (AE-0111)."""

    @pytest.mark.asyncio
    async def test_bootstrap_with_acl_wires_acl_backed_ports(
        self, session: AsyncSession
    ) -> None:
        from unittest.mock import MagicMock

        from rag_backend.modules.editorial.bootstrap import (
            EditorialAdapters,
            bootstrap_module,
        )

        project_id = await _seed_project(
            session,
            workflow_status=WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
            is_public=False,
        )
        adapters = EditorialAdapters(
            repository=AsyncMock(spec=CarouselRepository),
            unit_of_work=AsyncMock(),
            legacy_carousel_acl=_acl(session),
        )
        module = bootstrap_module(platform=MagicMock(), adapters=adapters)
        # The ACL-backed approval/release reads resolve through the wired ports.
        approval = await module.service.get_approval_state(project_id)
        release = await module.service.get_release_state(project_id)
        assert approval is not None and approval.is_approved is True
        assert release is not None and release.is_public is False
