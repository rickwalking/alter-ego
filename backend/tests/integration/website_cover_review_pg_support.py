"""Shared Postgres harness for the website cover switch in final review.

The generation service and runner, the asset store, the selection, the
review-switch store (project lock + lock-version CAS + ``FOR UPDATE``), the
autopilot run repository and the review hold are real; the image bridge is a
fake editor, the republish render is recorded instead of run, and every
Instagram call is recorded (none may happen).
"""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.application.services.carousel.cover_generation import (
    CoverGenerationRun,
    StartCoverGeneration,
)
from rag_backend.domain.constants.creator_asset import build_creator_asset_filename
from rag_backend.domain.models import CarouselProject
from rag_backend.infrastructure.database import config as db_config
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models import UserModel
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.carousel_creator_asset import (
    CarouselCreatorAssetModel,
)
from rag_backend.modules.autopilot import cover_review_hold
from rag_backend.modules.autopilot.domain.models import AutopilotRunState
from rag_backend.modules.autopilot.infrastructure.models import (
    AutopilotRunModel,
    TopicCandidateModel,
)
from rag_backend.modules.editorial.infrastructure import carousel_owner_autofix
from rag_backend.modules.editorial.public import (
    CarouselAutomationAcl,
    CoverReviewTarget,
    CoverRunWiring,
    cover_generation_service,
    reviewing_cover_task,
    selecting_cover_task,
)
from tests.integration.cover_generation_support import FakeEditor, cover_png

Task = Callable[[], Awaitable[object]]

_ROOT_TABLES = (
    "carousel_cover_generations",
    "carousel_creator_assets",
    "blog_posts",
    "autopilot_runs",
    "event_outbox",
    "workflow_audit_log",
)


def tables() -> list[str]:
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

    for root in _ROOT_TABLES:
        _visit(root)
    return ordered


@dataclass(frozen=True)
class RunFacts:
    """An autopilot run's state, reason and queued rework, as committed."""

    state: str
    reason: str | None
    rework_phase: str | None


@dataclass
class Harness:
    """The isolated engine, the fake bridge and what the stubs recorded."""

    engine: AsyncEngine
    editor: FakeEditor = field(default_factory=FakeEditor)
    renders: list[RunFacts | None] = field(default_factory=list)
    instagram: list[str] = field(default_factory=list)

    def sessions(self) -> async_sessionmaker[AsyncSession]:
        """A session maker on the isolated engine."""
        return async_sessionmaker(self.engine, expire_on_commit=False)


def harness(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> Harness:
    """Sessions on the isolated engine, a recorded render, recorded Instagram."""
    built = Harness(engine=engine)
    monkeypatch.setattr(db_config, "get_session_maker", built.sessions)

    async def _render(_self: object, project_id: str) -> tuple[str, ...]:
        built.renders.append(await run_facts(built, project_id))
        return ()

    monkeypatch.setattr(carousel_owner_autofix.RepublishRenderer, "render", _render)
    from rag_backend.modules.autopilot.infrastructure import instagram_gateway

    def _record(name: str) -> Callable[..., Awaitable[object]]:
        async def _call(*_args: object, **_kwargs: object) -> object:
            built.instagram.append(name)
            raise AssertionError(name)

        return _call

    for gateway in ("SteppedInstagramGateway", "AtomicInstagramGateway"):
        cls = getattr(instagram_gateway, gateway)
        monkeypatch.setattr(cls, "open_carousel", _record("open_carousel"))
        monkeypatch.setattr(cls, "publish_atomic", _record("publish_atomic"))
    return built


async def seed(built: Harness, assets: Path, **values: object) -> tuple[str, list[str]]:
    """A completed POV carousel in final review (draft) and two library photos."""
    owner_id, project_id = str(uuid4()), str(uuid4())
    photo_ids = [str(uuid4()), str(uuid4())]
    async with built.sessions()() as session:
        session.add(
            UserModel(
                id=owner_id,
                email=f"{owner_id}@pg.test",
                full_name="Owner",
                hashed_password="x",
                role="editor",
            )
        )
        await session.flush()
        for photo_id in photo_ids:
            digest = hashlib.sha256(photo_id.encode()).hexdigest()
            session.add(
                CarouselCreatorAssetModel(
                    id=photo_id,
                    owner_id=owner_id,
                    content_sha256=digest,
                    media_type="image/webp",
                    width=1080,
                    height=1350,
                    relative_path=f"{owner_id}/{digest}.webp",
                    role="hook",
                )
            )
            (assets / build_creator_asset_filename(digest)).write_bytes(cover_png())
        await session.flush()
        fields: dict[str, object] = {
            "status": "completed",
            "current_phase": "final_review",
            "phase_status": "awaiting_human",
            "workflow_status": "draft",
            "lock_version": 3,
            "hook_asset_id": photo_ids[0],
            **values,
        }
        session.add(
            CarouselProjectModel(
                id=project_id,
                topic="Agentes em produção",
                audience="Devs",
                niche="IA",
                owner_id=owner_id,
                content_mode="pov",
                **fields,
            )
        )
        await session.commit()
    return project_id, photo_ids


async def seed_run(built: Harness, project_id: str, state: AutopilotRunState) -> None:
    """An autopilot run for the carousel in ``state``."""
    topic_id = uuid4()
    now = datetime.now(UTC)
    async with built.engine.begin() as conn:
        await conn.execute(
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
        await conn.execute(
            insert(AutopilotRunModel).values(
                id=uuid4(),
                carousel_project_id=project_id,
                topic_candidate_id=topic_id,
                state=state.value,
                telegram_message_ids=[],
                created_at=now,
                updated_at=now,
            )
        )


async def run_facts(built: Harness, project_id: str) -> RunFacts | None:
    """The committed run of the carousel, or None."""
    async with built.sessions()() as session:
        row = await session.scalar(
            select(AutopilotRunModel).where(
                AutopilotRunModel.carousel_project_id == project_id
            )
        )
        if row is None:
            return None
        return RunFacts(
            state=str(row.state),
            reason=row.state_reason,
            rework_phase=row.rework_phase,
        )


async def row(built: Harness, project_id: str) -> CarouselProjectModel:
    """The committed carousel row."""
    async with built.sessions()() as session:
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        return model


def _wiring(built: Harness) -> CoverRunWiring:
    return CoverRunWiring(
        editor=built.editor,
        render_prompt=lambda text: text,
        now=lambda: datetime.now(UTC),
    )


async def _start(
    built: Harness, project_id: str, photo: str
) -> tuple[CarouselProject, CoverGenerationRun]:
    async with built.sessions()() as session:
        project = await CarouselAutomationAcl(session).load_project(project_id)
        assert project is not None
        run = await cover_generation_service(session).start(
            StartCoverGeneration(
                project=project,
                user_id=project.owner_id or "",
                photo_ids=(UUID(photo),),
                prompt="Uma capa",
                confirmed=True,
            )
        )
    return project, run


async def website_task(built: Harness, project_id: str, photo: str) -> Task:
    """The owner's "Gerar capa com Grok" run, composed as the route does."""
    project, run = await _start(built, project_id, photo)
    target = CoverReviewTarget(project=project, hold=cover_review_hold())
    return reviewing_cover_task(_wiring(built), run, target)


async def autopilot_task(built: Harness, project_id: str, photo: str) -> Task:
    """An autopilot-started run (no review switch), as the autostart schedules it."""
    project, run = await _start(built, project_id, photo)
    return selecting_cover_task(_wiring(built), run, project)


async def result_asset(built: Harness, project_id: str) -> str | None:
    """The stored result of the carousel's only generation."""
    from rag_backend.modules.editorial.infrastructure.cover_generations import (
        SqlCoverGenerationRepository,
    )

    async with built.sessions()() as session:
        rows = await SqlCoverGenerationRepository(session).for_project(project_id)
    assert len(rows) == 1
    found = rows[0].result_asset_id
    return str(found) if found else None


__all__ = [
    "Harness",
    "RunFacts",
    "Task",
    "autopilot_task",
    "harness",
    "result_asset",
    "row",
    "run_facts",
    "seed",
    "seed_run",
    "tables",
    "website_task",
]
