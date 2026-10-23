"""Shared helpers of the Grok cover generation integration tests.

Feature: Generate a slide-1 cover from library photos with Grok
(tests/features/cover_generation_ae0508.feature). A fake image bridge editor
that records each job and answers a generated image (or fails), carousel and
generation-row helpers over the in-memory database. Photos are generated.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

import pytest
from httpx import AsyncClient
from PIL import Image

from rag_backend.api.routes.carousels import cover_generate as route
from rag_backend.api.routes.carousels import cover_pick as cover_pick_route
from rag_backend.application.services.carousel.cover_generation_tasks import (
    running_cover_generation_tasks,
)
from rag_backend.domain.models.cover_generation import CoverEditJob
from rag_backend.modules.editorial.infrastructure import carousel_owner_autofix
from rag_backend.modules.editorial.public import CoverRunWiring

THESIS = "A IA escreve código. Quem decide ainda é você."
RED = (200, 10, 10, 0)
BLUE = (10, 10, 200, 0)
PROMPT = "Eu num café em Lisboa, luz de fim de tarde"


def cover_png(size: tuple[int, int] = (1080, 1350)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (30, 120, 200)).save(buffer, format="PNG")
    return buffer.getvalue()


@dataclass
class FakeEditor:
    """Records each job; answers ``image`` or raises ``error``."""

    image: bytes = field(default_factory=cover_png)
    error: Exception | None = None
    jobs: list[CoverEditJob] = field(default_factory=list)

    async def edit_image(self, job: CoverEditJob) -> bytes:
        self.jobs.append(job)
        if self.error is not None:
            raise self.error
        return self.image


def install_fake_editor(monkeypatch: pytest.MonkeyPatch) -> FakeEditor:
    """Route the cover generation through a fake bridge editor."""
    fake = FakeEditor()

    def _wiring(render_prompt: object) -> CoverRunWiring:
        del render_prompt
        return CoverRunWiring(
            editor=fake,
            render_prompt=lambda text: f"direction: {text}",
            now=lambda: datetime.now(UTC),
        )

    monkeypatch.setattr(route, "cover_run_wiring", _wiring)
    return fake


def install_renders(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Stub the republish renderer and the GrokBot offer; the rendered ids."""
    calls: list[str] = []

    async def _render(_self: object, project_id: str) -> tuple[str, ...]:
        calls.append(project_id)
        return ()

    monkeypatch.setattr(carousel_owner_autofix.RepublishRenderer, "render", _render)

    class _NoOffer:
        async def offer(self, project_id: str) -> None:
            del project_id

    monkeypatch.setattr(cover_pick_route, "project_cover_offer", lambda _db: _NoOffer())
    return calls


async def project(client: AsyncClient, photo_id: object, mode: str = "pov") -> str:
    body: dict[str, object] = {"topic": "T", "audience": "Devs", "niche": "IA"}
    if mode != "news_analysis":
        body |= {"content_mode": mode, "pov_thesis": THESIS, "hook_asset_id": photo_id}
    created = await client.post("/api/carousels", json=body)
    assert created.status_code == 201, created.text
    project_id = str(created.json()["id"])
    await set_project(
        project_id, status="completed", phase_status="awaiting_human", lock_version=4
    )
    return project_id


async def set_project(project_id: str, **values: object) -> None:
    from sqlalchemy import update

    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

    async with get_session_maker()() as session:
        await session.execute(
            update(CarouselProjectModel)
            .where(CarouselProjectModel.id == project_id)
            .values(**values)
        )
        await session.commit()


async def slide_cover(project_id: str) -> dict[str, object]:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

    async with get_session_maker()() as session:
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        assert isinstance(model.slide_cover, dict)
        return dict(model.slide_cover)


async def generation_rows(project_id: str | None = None) -> list[dict[str, object]]:
    from sqlalchemy import select

    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models import (
        CarouselCoverGenerationModel as Row,
    )

    async with get_session_maker()() as session:
        query = select(Row)
        if project_id is not None:
            query = query.where(Row.project_id == project_id)
        rows = await session.scalars(query)
        return [
            {
                "status": row.status,
                "error_code": row.error_code,
                "result_asset_id": row.result_asset_id,
                "prompt_sha256": row.prompt_sha256,
                "owner_id": row.owner_id,
            }
            for row in rows
        ]


async def insert_rows(project_id: str, rows: list[tuple[str, datetime]]) -> None:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models import (
        CarouselCoverGenerationModel as Row,
    )
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

    async with get_session_maker()() as session:
        project = await session.get(CarouselProjectModel, project_id)
        assert project is not None
        for status, created_at in rows:
            session.add(
                Row(
                    id=str(uuid4()),
                    project_id=project_id,
                    owner_id=project.owner_id,
                    status=status,
                    prompt_sha256="0" * 64,
                    photo_count=1,
                    model="m",
                    cost_usd=0.0,
                    created_at=created_at,
                )
            )
        await session.commit()


async def role_cover_assets() -> list[str]:
    from sqlalchemy import select

    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models import CarouselCreatorAssetModel

    async with get_session_maker()() as session:
        rows = await session.scalars(
            select(CarouselCreatorAssetModel.id).where(
                CarouselCreatorAssetModel.role == "cover"
            )
        )
        return [str(row) for row in rows]


async def drain() -> None:
    await asyncio.gather(*running_cover_generation_tasks())


def request_body(photo_ids: list[object], confirmed: bool = True) -> dict[str, object]:
    return {
        "photo_ids": [str(p) for p in photo_ids],
        "prompt": PROMPT,
        "confirmed": confirmed,
    }


async def generate(
    client: AsyncClient, project_id: str, photo_ids: list[object]
) -> dict[str, object]:
    response = await client.post(
        f"/api/carousels/{project_id}/cover-generations", json=request_body(photo_ids)
    )
    assert response.status_code == 202, response.text
    await drain()
    body = response.json()
    assert isinstance(body, dict)
    return body
