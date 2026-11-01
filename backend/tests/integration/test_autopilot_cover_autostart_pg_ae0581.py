"""The autopilot auto-cover through the real stack, on Postgres.

Feature: Autopilot auto-cover for new carousels
(tests/features/autopilot_cover_autostart_ae0581.feature). The repository, the
photo library and the CoverGenerationService are real; only the image bridge
and the background task are stubbed. Skipped without a Postgres
``DATABASE_URL`` (CI sets one).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from rag_backend.domain.constants.creator_asset import build_creator_asset_filename
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models import (
    CarouselCoverGenerationModel,
    UserModel,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.carousel_creator_asset import (
    CarouselCreatorAssetModel,
)
from rag_backend.modules.editorial.infrastructure import (
    carousel_cover_autoselect,
    carousel_cover_autostart,
)
from rag_backend.modules.editorial.infrastructure.carousel_cover_autostart import (
    schedule_autopilot_cover,
)
from rag_backend.modules.editorial.infrastructure.cover_generations import (
    SqlCoverGenerationRepository,
)
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

_ROOT_TABLES = ("carousel_cover_generations", "carousel_creator_assets", "blog_posts")


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

    for root in _ROOT_TABLES:
        _visit(root)
    return ordered


def _fake_bridge(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Stub the bridge wiring and the background task; returns scheduled ids."""
    scheduled: list[str] = []
    monkeypatch.setattr(
        carousel_cover_autostart, "cover_run_wiring", lambda _render: object()
    )
    monkeypatch.setattr(
        carousel_cover_autoselect, "cover_generation_task", lambda _w, run: run
    )
    from rag_backend.application.services.carousel import cover_generation_tasks

    monkeypatch.setattr(
        cover_generation_tasks,
        "schedule_cover_generation",
        lambda run, generation_id: scheduled.append(generation_id),
    )
    return scheduled


async def _seed(engine: AsyncEngine, assets_root: Path) -> tuple[str, str, int]:
    """An owner, a POV carousel and two library photos with stored files."""
    owner_id, project_id = str(uuid4()), str(uuid4())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
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
        session.add(
            CarouselProjectModel(
                id=project_id,
                topic="Agentes em produção",
                audience="Devs",
                niche="IA",
                owner_id=owner_id,
                content_mode="pov",
            )
        )
        await session.flush()
        for index in range(2):
            digest = hashlib.sha256(f"photo-{project_id}-{index}".encode()).hexdigest()
            session.add(
                CarouselCreatorAssetModel(
                    id=str(uuid4()),
                    owner_id=owner_id,
                    content_sha256=digest,
                    media_type="image/webp",
                    width=10,
                    height=10,
                    relative_path=f"{owner_id}/{digest}.webp",
                    role="hook",
                )
            )
            (assets_root / build_creator_asset_filename(digest)).write_bytes(b"x")
        await session.commit()
    return owner_id, project_id, 2


@requires_postgres
@pytest.mark.asyncio
async def test_real_path_records_one_pending_job_and_dedups(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: A fresh autopilot carousel gets one cover job."""
    assets = tmp_path / "assets"
    assets.mkdir()
    monkeypatch.setenv("CAROUSEL_CREATOR_ASSETS_DIR", str(assets))
    get_settings.cache_clear()
    scheduled = _fake_bridge(monkeypatch)
    async with isolated_schema(_tables()) as engine:
        owner_id, project_id, photo_count = await _seed(engine, assets)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            outcome = await schedule_autopilot_cover(session, project_id)
            assert outcome.scheduled
            assert scheduled == [outcome.generation_id]
            rows = await SqlCoverGenerationRepository(session).for_project(project_id)
            assert len(rows) == 1
            assert rows[0].photo_count == photo_count
            assert rows[0].owner_id == owner_id

            again = await schedule_autopilot_cover(session, project_id)
            assert not again.scheduled
            assert again.reason == "already_exists"
            assert len(scheduled) == 1


@requires_postgres
@pytest.mark.asyncio
async def test_real_path_respects_the_carousel_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: A cap refusal skips the job."""
    assets = tmp_path / "assets"
    assets.mkdir()
    monkeypatch.setenv("CAROUSEL_CREATOR_ASSETS_DIR", str(assets))
    get_settings.cache_clear()
    scheduled = _fake_bridge(monkeypatch)
    async with isolated_schema(_tables()) as engine:
        owner_id, project_id, _ = await _seed(engine, assets)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        other_id = str(uuid4())
        async with factory() as session:
            session.add(
                CarouselProjectModel(
                    id=other_id,
                    topic="Outro",
                    audience="Devs",
                    niche="IA",
                    owner_id=owner_id,
                    content_mode="pov",
                )
            )
            now = datetime.now(UTC)
            for _ in range(40):
                session.add(
                    CarouselCoverGenerationModel(
                        id=str(uuid4()),
                        project_id=other_id,
                        owner_id=owner_id,
                        status="succeeded",
                        prompt_sha256="0" * 64,
                        photo_count=1,
                        model="m",
                        cost_usd=0.0,
                        created_at=now,
                    )
                )
            await session.commit()
            outcome = await schedule_autopilot_cover(session, project_id)
            assert not outcome.scheduled
            assert outcome.reason.endswith("cover_generation_monthly_cap")
            assert scheduled == []
