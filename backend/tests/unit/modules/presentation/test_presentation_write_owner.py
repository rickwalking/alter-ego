"""Contract + concurrency tests for the presentation persistence owner / ACL
(AE-0118).

These cover the AE-0118 acceptance criteria at the adapter boundary:

* **Read-side mapping** — a legacy ``CarouselProjectModel`` translates into the
  presentation VIEW (``PresentationProject`` wrapped in
  ``PresentationProjectView``) with the canonical ``CarouselProject`` surfaced and
  the ``lock_version`` token read verbatim.
* **Write delegation** — the presentation-owned writes (design-token refresh,
  presentation columns, slide create/update) go THROUGH the
  :class:`PresentationWriteOwner` (flush only) and commit via the platform Unit of
  Work; the persisted DB state proves the delegation, and the owner is the single
  committer.
* **artifact_version <-> lock_version compound CAS preserved exactly** — the
  owner's activation path bumps BOTH columns atomically by exactly one against the
  compound guard, and a stale source is rejected with
  ``ERR_ARTIFACT_BUILD_CONFLICT`` (never a silent overwrite).
* **Shared-owner no-clobber concurrency** — a presentation activation bump and an
  editorial resume bump race the SHARED ``lock_version`` token from the same
  source version; exactly one succeeds, the loser gets its conflict
  (``ERR_ARTIFACT_BUILD_CONFLICT`` / ``ERR_VERSION_CONFLICT``), and
  ``lock_version`` advances by exactly one per success (no lost update).

Behavior-preserving adapter; verified here + by the AE-0116 safety net. External
clients are never constructed; the tests use an in-memory SQLite session — no API
keys required.

Feature file: tests/features/presentation_persistence_acl.feature
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.domain.constants.artifact_build import ERR_ARTIFACT_BUILD_CONFLICT
from rag_backend.domain.constants.carousel_presentation import (
    ARTIFACT_BUILD_STATUS_READY,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.models import CarouselProject, CarouselSlide
from rag_backend.domain.models.carousel import DesignTokens
from rag_backend.infrastructure.database.carousel_artifact_build_repository import (
    _ActivateBuildParams,
)
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.carousel_artifact_build import (
    CarouselArtifactBuildModel,
)
from rag_backend.modules.editorial.infrastructure.carousel_project_write_owner import (
    CarouselProjectWriteOwner,
)
from rag_backend.modules.presentation.public import (
    PresentationPersistenceAcl,
    PresentationProject,
    PresentationProjectView,
    PresentationWriteOwner,
)

_TOPIC = "Presentation persistence"
_AUDIENCE = "Developers"
_NICHE = "Tech"
_OUTPUT_DIR = "/tmp/ae-0118-output"
_NEW_PDF_PT = "/tmp/ae-0118-output/pt/carousel.pdf"
_NEW_PDF_EN = "/tmp/ae-0118-output/en/carousel.pdf"
_ARTIFACT_V1 = "artifact_v1"

_DESIGN_TOKENS: DesignTokens = cast(
    DesignTokens,
    {
        "colors": {"primary": "#3b82f6", "accent": "#f59e0b"},
        "typography": {"font_family_heading": "Inter"},
        "images": {"hero": "", "slides": []},
        "layout": {"badge_label": "AE0118", "progress_segments": 3},
    },
)


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
    artifact_version: str | None = None,
) -> str:
    """Persist a carousel row and return its id."""
    project_id = str(uuid.uuid4())
    model = CarouselProjectModel(
        id=project_id,
        topic=_TOPIC,
        audience=_AUDIENCE,
        niche=_NICHE,
        output_dir=_OUTPUT_DIR,
        lock_version=lock_version,
        artifact_version=artifact_version,
    )
    session.add(model)
    await session.commit()
    return project_id


async def _seed_ready_build(
    session: AsyncSession,
    project_id: str,
    artifact_version: str,
    source_lock_version: int,
) -> None:
    """Persist a READY artifact-build record the activation CAS promotes to ACTIVE.

    The activation CAS (``activate_build``) flips the matching build row to
    ACTIVE; without a pre-existing build record its final ``rowcount`` would be 0.
    The real flow upserts this READY record before activating; the test mirrors
    that precondition.
    """
    build = CarouselArtifactBuildModel(
        id=str(uuid.uuid4()),
        project_id=project_id,
        artifact_version=artifact_version,
        operation_id=f"op-{artifact_version}",
        source_lock_version=source_lock_version,
        status=ARTIFACT_BUILD_STATUS_READY,
    )
    session.add(build)
    await session.commit()


def _acl(session: AsyncSession) -> PresentationPersistenceAcl:
    """Build the ACL over a real presentation write owner."""
    return PresentationPersistenceAcl(session, PresentationWriteOwner(session))


# === Read-side mapping =========================================================
class TestReadSideMapping:
    """Scenario: a legacy row maps to the presentation VIEW."""

    @pytest.mark.asyncio
    async def test_to_presentation_surfaces_canonical_entity(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session, artifact_version=_ARTIFACT_V1)
        view = await _acl(session).load_presentation(project_id)

        assert view is not None
        assert isinstance(view, PresentationProjectView)
        assert isinstance(view.presentation, PresentationProject)
        assert isinstance(view.project, CarouselProject)
        assert view.project.topic == _TOPIC
        assert str(view.project.id) == project_id
        assert view.presentation.artifact_version == _ARTIFACT_V1

    @pytest.mark.asyncio
    async def test_lock_version_surfaced_verbatim(self, session: AsyncSession) -> None:
        project_id = await _seed_project(session, lock_version=5)
        view = await _acl(session).load_presentation(project_id)

        assert view is not None
        assert view.lock_version == 5

    @pytest.mark.asyncio
    async def test_load_returns_none_when_absent(self, session: AsyncSession) -> None:
        view = await _acl(session).load_presentation(str(uuid.uuid4()))
        assert view is None


# === Write delegation ==========================================================
class TestWriteDelegation:
    """Scenario: presentation writes go THROUGH the single write owner."""

    @pytest.mark.asyncio
    async def test_refresh_design_tokens_persists_via_owner(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session)
        acl = _acl(session)
        view = await acl.load_presentation(project_id)
        assert view is not None

        await acl.refresh_design_tokens(view.project, _DESIGN_TOKENS)
        # Not yet committed: the owner only flushed. Commit is the owner's job.
        await acl.commit()

        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        assert model.design_tokens == _DESIGN_TOKENS

    @pytest.mark.asyncio
    async def test_update_project_persists_presentation_columns(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session)
        acl = _acl(session)
        view = await acl.load_presentation(project_id)
        assert view is not None

        entity = view.project
        entity.pdf_path = _NEW_PDF_PT
        entity.pdf_path_en = _NEW_PDF_EN
        entity.slide_layout_strategy = "grid"
        entity.presentation_policy_version = "v3"
        entity.creator_name = "Pedro"
        await acl.update_project(entity)
        await acl.commit()

        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        assert model.pdf_path == _NEW_PDF_PT
        assert model.pdf_path_en == _NEW_PDF_EN
        assert model.slide_layout_strategy == "grid"
        assert model.presentation_policy_version == "v3"
        assert model.creator_name == "Pedro"

    @pytest.mark.asyncio
    async def test_update_absent_project_raises(self, session: AsyncSession) -> None:
        acl = _acl(session)
        ghost = CarouselProject(
            topic=_TOPIC, audience=_AUDIENCE, niche=_NICHE, output_dir=_OUTPUT_DIR
        )
        with pytest.raises(ValueError):
            await acl.update_project(ghost)


# === Slide-write contract ======================================================
class TestSlideWriteContract:
    """Scenario: slide rows are created and updated through the owner."""

    @pytest.mark.asyncio
    async def test_create_then_update_slide_via_owner(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session)
        acl = _acl(session)
        slide = CarouselSlide(
            project_id=uuid.UUID(project_id),
            slide_number=1,
            slide_type="content",
            heading="Original heading",
            body="Original body",
            image_prompt="Prompt 1",
        )
        await acl.create_slide(slide)
        await acl.commit()

        from rag_backend.infrastructure.database.models.carousel import (
            CarouselSlideModel,
        )

        persisted_created = await session.get(CarouselSlideModel, str(slide.id))
        assert persisted_created is not None
        assert persisted_created.heading == "Original heading"

        slide.heading = "Updated heading"
        slide.body = "Updated body"
        slide.image_path = "/tmp/ae-0118-output/images/slide_1.jpg"
        await acl.update_slide(slide)
        await acl.commit()

        persisted = await session.get(CarouselSlideModel, str(slide.id))
        assert persisted is not None
        assert persisted.heading == "Updated heading"
        assert persisted.body == "Updated body"
        assert persisted.image_path == "/tmp/ae-0118-output/images/slide_1.jpg"

    @pytest.mark.asyncio
    async def test_update_absent_slide_raises(self, session: AsyncSession) -> None:
        await _seed_project(session)
        acl = _acl(session)
        ghost = CarouselSlide(
            project_id=uuid.uuid4(),
            slide_number=1,
            slide_type="content",
            heading="x",
            body="y",
        )
        with pytest.raises(ValueError):
            await acl.update_slide(ghost)


# === Activation CAS (artifact_version <-> lock_version) =========================
class TestActivationCasPreserved:
    """Scenario: the activation CAS preserves the compound pairing exactly."""

    @pytest.mark.asyncio
    async def test_activation_bumps_both_columns_by_one(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session, lock_version=1, artifact_version=None)
        await _seed_ready_build(
            session, project_id, _ARTIFACT_V1, source_lock_version=1
        )
        acl = _acl(session)

        new_lock = await acl.activate_artifact(
            _ActivateBuildParams(
                project_id=uuid.UUID(project_id),
                artifact_version=_ARTIFACT_V1,
                source_lock_version=1,
                prior_artifact_version=None,
            )
        )
        await acl.commit()

        assert new_lock == 2
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        # The compound pairing: BOTH artifact_version and lock_version moved as one.
        assert model.artifact_version == _ARTIFACT_V1
        assert model.lock_version == 2

    @pytest.mark.asyncio
    async def test_stale_source_lock_version_is_rejected(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session, lock_version=4, artifact_version=None)
        acl = _acl(session)

        # The activation expects source_lock_version=2 but the row is at 4.
        with pytest.raises(ValueError) as exc:
            await acl.activate_artifact(
                _ActivateBuildParams(
                    project_id=uuid.UUID(project_id),
                    artifact_version=_ARTIFACT_V1,
                    source_lock_version=2,
                    prior_artifact_version=None,
                )
            )
        assert str(exc.value) == ERR_ARTIFACT_BUILD_CONFLICT

        # No silent overwrite: the row is unchanged.
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        assert model.lock_version == 4
        assert model.artifact_version is None


# === Shared-owner no-clobber concurrency =======================================
class TestSharedLockNoClobber:
    """Scenario Outline: activation + resume bumps cannot interleave-clobber.

    Both the presentation activation CAS and the editorial resume CAS bump the
    SAME ``lock_version`` token from the same source version. The DB-level
    compare-and-swap (``WHERE lock_version = source``) is the single shared
    primitive: whichever runs second sees the already-advanced version and loses
    with its own conflict error, so ``lock_version`` advances by exactly one and
    no update is lost.
    """

    @pytest.mark.asyncio
    async def test_activation_then_resume_serializes(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session, lock_version=1, artifact_version=None)
        await _seed_ready_build(
            session, project_id, _ARTIFACT_V1, source_lock_version=1
        )
        presentation = PresentationWriteOwner(session)
        editorial = CarouselProjectWriteOwner(session)

        # Activation wins first: lock_version 1 -> 2 (paired with artifact_version).
        new_lock = await presentation.activate_artifact(
            _ActivateBuildParams(
                project_id=uuid.UUID(project_id),
                artifact_version=_ARTIFACT_V1,
                source_lock_version=1,
                prior_artifact_version=None,
            )
        )
        assert new_lock == 2

        # The editorial resume bump holds the now-stale source version 1 -> loses.
        with pytest.raises(ValueError) as exc:
            await editorial.bump_resume_lock_version(project_id, expected_version=1)
        assert str(exc.value) == ERR_VERSION_CONFLICT

        await presentation.commit()
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        # Exactly one success: lock advanced by exactly one; artifact stayed paired.
        assert model.lock_version == 2
        assert model.artifact_version == _ARTIFACT_V1

    @pytest.mark.asyncio
    async def test_resume_then_activation_serializes(
        self, session: AsyncSession
    ) -> None:
        project_id = await _seed_project(session, lock_version=1, artifact_version=None)
        presentation = PresentationWriteOwner(session)
        editorial = CarouselProjectWriteOwner(session)

        # Resume wins first: lock_version 1 -> 2 (no artifact change).
        new_version = await editorial.bump_resume_lock_version(
            project_id, expected_version=1
        )
        assert new_version == 2

        # The activation holds the now-stale source version 1 -> loses; its
        # compound guard (lock_version == 1) no longer matches.
        with pytest.raises(ValueError) as exc:
            await presentation.activate_artifact(
                _ActivateBuildParams(
                    project_id=uuid.UUID(project_id),
                    artifact_version=_ARTIFACT_V1,
                    source_lock_version=1,
                    prior_artifact_version=None,
                )
            )
        assert str(exc.value) == ERR_ARTIFACT_BUILD_CONFLICT

        await editorial.commit()
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        # Exactly one success: lock advanced by exactly one; activation lost so
        # artifact_version stayed unset (no silent overwrite of the shared token).
        assert model.lock_version == 2
        assert model.artifact_version is None

    @pytest.mark.asyncio
    async def test_both_succeed_when_each_reads_fresh_version(
        self, session: AsyncSession
    ) -> None:
        """Sequential bumps with refreshed expected versions each advance by one."""
        project_id = await _seed_project(session, lock_version=1, artifact_version=None)
        await _seed_ready_build(
            session, project_id, _ARTIFACT_V1, source_lock_version=2
        )
        presentation = PresentationWriteOwner(session)
        editorial = CarouselProjectWriteOwner(session)

        after_resume = await editorial.bump_resume_lock_version(
            project_id, expected_version=1
        )
        assert after_resume == 2

        # The activation now uses the FRESH source (2) -> succeeds, lock -> 3.
        after_activation = await presentation.activate_artifact(
            _ActivateBuildParams(
                project_id=uuid.UUID(project_id),
                artifact_version=_ARTIFACT_V1,
                source_lock_version=2,
                prior_artifact_version=None,
            )
        )
        assert after_activation == 3

        await presentation.commit()
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        assert model.lock_version == 3
        assert model.artifact_version == _ARTIFACT_V1
