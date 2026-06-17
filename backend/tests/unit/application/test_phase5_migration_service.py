"""Unit tests for Phase5MigrationService.

Feature: phase5_migration_launch.feature
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.application.services.phase5_migration_service import (
    Phase5MigrationService,
    build_creative_brief,
)
from rag_backend.domain.constants.blog_post import BlogPostOrigin
from rag_backend.domain.constants.carousel import (
    CAROUSEL_STATUS_COMPLETED,
    CAROUSEL_STATUS_RESEARCHING,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_RESEARCH,
    PHASE_STATUS_IN_PROGRESS,
)
from rag_backend.domain.constants.migration import (
    DEFAULT_PERSONA_NAME,
    DEFAULT_RUBRIC_NAME,
)
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.distribution_home import read_distribution
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.persona_rubric import (
    PersonaProfileModel,
    QualityRubricModel,
)


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        yield db
    await engine.dispose()


def _reader(db: AsyncSession):
    """Bind the canonical-home reader to the test session (AE-0204 DI)."""

    async def _read(project_id: str) -> dict[str, str | None] | None:
        return await read_distribution(db, project_id)

    return _read


async def _seed_distribution(
    db: AsyncSession, project: CarouselProjectModel, *, caption: str
) -> None:
    """Seed the carousel-origin blog row + its distribution (the canonical home).

    AE-0204: the persona writing samples are now sourced from the canonical home,
    so tests seed it explicitly instead of relying on the embedded caption column.
    """
    db.add(
        BlogPostModel.from_entity({
            "id": str(uuid.uuid4()),
            "project_id": project.id,
            "origin": BlogPostOrigin.CAROUSEL.value,
            "title": "t",
            "slug": f"carousel-{project.id}",
            "status": "published",
            "content": {"markdown": "# body"},
            "distribution": {
                "caption": caption,
                "linkedin_post_pt": None,
                "linkedin_post_en": None,
            },
        })
    )


def _project(**overrides: object) -> CarouselProjectModel:
    now = datetime.now(UTC)
    defaults = {
        "id": str(uuid.uuid4()),
        "topic": "AI agents",
        "audience": "Developers",
        "niche": "Tech",
        "title": "Building Agents",
        "subtitle": "A practical guide",
        "slides_config": "5 slides",
        "aspect_ratio": "4:5",
        "language": "en",
        "theme": "auto",
        "image_style": "comic_neon",
        "status": CAROUSEL_STATUS_RESEARCHING,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return CarouselProjectModel(**defaults)  # type: ignore[arg-type]


class TestBuildCreativeBrief:
    # Scenario: MIG-001 Migrate creative brief from legacy fields
    def test_builds_brief_from_legacy_fields(self) -> None:
        project = _project(creative_brief=None)
        brief = build_creative_brief(project)
        assert "AI agents" in brief
        assert "Developers" in brief
        assert "Building Agents" in brief


@pytest.mark.asyncio
class TestPhase5MigrationService:
    # Scenario: MIG-001
    async def test_migrate_creative_brief(self, session: AsyncSession) -> None:
        project = _project(creative_brief=None)
        session.add(project)
        await session.commit()

        report = await Phase5MigrationService().run(session, _reader(session), dry_run=False)

        await session.refresh(project)
        assert report.creative_briefs_updated == 1
        assert project.creative_brief is not None
        assert "AI agents" in project.creative_brief

    # Scenario: MIG-004
    async def test_backfill_workflow_state(self, session: AsyncSession) -> None:
        project = _project(status=CAROUSEL_STATUS_RESEARCHING, current_phase="brief")
        session.add(project)
        await session.commit()

        report = await Phase5MigrationService().run(session, _reader(session), dry_run=False)

        await session.refresh(project)
        assert report.workflow_states_updated >= 1
        assert project.current_phase == PHASE_RESEARCH
        assert project.phase_status == PHASE_STATUS_IN_PROGRESS

    # Scenario: MIG-002
    async def test_creates_default_persona_from_outputs(
        self, session: AsyncSession
    ) -> None:
        completed = _project(
            status=CAROUSEL_STATUS_COMPLETED,
            blog_markdown="Deep dive into agent orchestration patterns.",
        )
        session.add(completed)
        # AE-0204: the caption sample is sourced from the canonical home.
        await _seed_distribution(
            session, completed, caption="Hook readers with a bold opening."
        )
        await session.commit()

        report = await Phase5MigrationService().run(
            session, _reader(session), dry_run=False
        )

        assert report.persona_created is True
        assert report.persona_id is not None
        persona = await session.get(PersonaProfileModel, report.persona_id)
        assert persona is not None
        assert persona.name == DEFAULT_PERSONA_NAME
        assert len(persona.writing_samples) >= 1
        # The caption sample came from the canonical home (AE-0204).
        assert "Hook readers with a bold opening." in persona.writing_samples

    # Scenario: MIG-003
    async def test_creates_default_rubric(self, session: AsyncSession) -> None:
        completed = _project(status=CAROUSEL_STATUS_COMPLETED)
        session.add(completed)
        await _seed_distribution(
            session, completed, caption="Sample caption for rubric seed."
        )
        await session.commit()

        report = await Phase5MigrationService().run(
            session, _reader(session), dry_run=False
        )

        assert report.rubric_created is True
        assert report.rubric_id is not None
        rubric = await session.get(QualityRubricModel, report.rubric_id)
        assert rubric is not None
        assert rubric.name == DEFAULT_RUBRIC_NAME
        assert rubric.is_default is True
        assert len(rubric.criteria) == 4

    async def test_dry_run_does_not_persist(self, session: AsyncSession) -> None:
        project = _project(creative_brief=None)
        session.add(project)
        await session.commit()

        report = await Phase5MigrationService().run(session, _reader(session), dry_run=True)

        await session.refresh(project)
        assert report.dry_run is True
        assert project.creative_brief is None

    async def test_links_persona_and_rubric_to_projects(
        self, session: AsyncSession
    ) -> None:
        project = _project(status=CAROUSEL_STATUS_COMPLETED)
        session.add(project)
        await _seed_distribution(session, project, caption="Linked sample text.")
        await session.commit()

        report = await Phase5MigrationService().run(
            session, _reader(session), dry_run=False
        )

        await session.refresh(project)
        assert project.persona_id == report.persona_id
        assert project.rubric_id == report.rubric_id
        assert report.projects_linked >= 1
