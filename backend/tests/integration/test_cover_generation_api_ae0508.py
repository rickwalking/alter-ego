"""Grok cover generation from library photos over HTTP.

Feature: Generate a slide-1 cover from library photos with Grok
(tests/features/cover_generation_ae0508.feature). The real app over an
in-memory SQLite database; the image bridge editor is a fake that records the
job and answers a generated image (or fails). Photos are generated, never real.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from PIL import Image
from structlog.testing import capture_logs

from rag_backend.api.routes.carousels import cover_generate as route
from rag_backend.api.routes.carousels import cover_pick as cover_pick_route
from rag_backend.application.services.carousel.cover_generation_tasks import (
    running_cover_generation_tasks,
)
from rag_backend.domain.models import UserRole
from rag_backend.domain.models.cover_generation import CoverEditJob
from rag_backend.modules.editorial.infrastructure import carousel_owner_autofix
from rag_backend.modules.editorial.public import CoverRunWiring
from tests.integration.conftest import auth_headers_for, create_test_user
from tests.integration.hook_photo_support import upload_photo

_THESIS = "A IA escreve código. Quem decide ainda é você."
_RED = (200, 10, 10, 0)
_BLUE = (10, 10, 200, 0)
_PROMPT = "Eu num café em Lisboa, luz de fim de tarde"


def _cover_png(size: tuple[int, int] = (1080, 1350)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (30, 120, 200)).save(buffer, format="PNG")
    return buffer.getvalue()


@dataclass
class _FakeEditor:
    """Records each job; answers ``image`` or raises ``error``."""

    image: bytes = field(default_factory=_cover_png)
    error: Exception | None = None
    jobs: list[CoverEditJob] = field(default_factory=list)

    async def edit_image(self, job: CoverEditJob) -> bytes:
        self.jobs.append(job)
        if self.error is not None:
            raise self.error
        return self.image


@pytest.fixture(autouse=True)
def _fresh_limiter() -> Iterator[None]:
    from rag_backend.api.middleware.rate_limiting import limiter

    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def editor(monkeypatch: pytest.MonkeyPatch) -> _FakeEditor:
    fake = _FakeEditor()

    def _wiring(render_prompt: object) -> CoverRunWiring:
        del render_prompt
        return CoverRunWiring(
            editor=fake,
            render_prompt=lambda text: f"direction: {text}",
            now=lambda: datetime.now(UTC),
        )

    monkeypatch.setattr(route, "cover_run_wiring", _wiring)
    return fake


@pytest.fixture
def renders(monkeypatch: pytest.MonkeyPatch) -> list[str]:
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


async def _project(client: AsyncClient, photo_id: object, mode: str = "pov") -> str:
    body: dict[str, object] = {"topic": "T", "audience": "Devs", "niche": "IA"}
    if mode != "news_analysis":
        body |= {"content_mode": mode, "pov_thesis": _THESIS, "hook_asset_id": photo_id}
    created = await client.post("/api/carousels", json=body)
    assert created.status_code == 201, created.text
    project_id = str(created.json()["id"])
    await _set(
        project_id, status="completed", phase_status="awaiting_human", lock_version=4
    )
    return project_id


async def _set(project_id: str, **values: object) -> None:
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


async def _slide_cover(project_id: str) -> dict[str, object]:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

    async with get_session_maker()() as session:
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        assert isinstance(model.slide_cover, dict)
        return dict(model.slide_cover)


async def _generation_rows(project_id: str | None = None) -> list[dict[str, object]]:
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


async def _insert_rows(project_id: str, rows: list[tuple[str, datetime]]) -> None:
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


async def _role_cover_assets() -> list[str]:
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


async def _drain() -> None:
    await asyncio.gather(*running_cover_generation_tasks())


def _body(photo_ids: list[object], confirmed: bool = True) -> dict[str, object]:
    return {
        "photo_ids": [str(p) for p in photo_ids],
        "prompt": _PROMPT,
        "confirmed": confirmed,
    }


async def _generate(
    client: AsyncClient, project_id: str, photo_ids: list[object]
) -> dict[str, object]:
    response = await client.post(
        f"/api/carousels/{project_id}/cover-generations", json=_body(photo_ids)
    )
    assert response.status_code == 202, response.text
    await _drain()
    body = response.json()
    assert isinstance(body, dict)
    return body


@pytest.mark.integration
class TestGenerate:
    async def test_confirmed_generation_stores_a_private_cover(
        self, client: AsyncClient, asset_dirs: Path, editor: _FakeEditor
    ) -> None:
        """Scenario: A confirmed generation sends the photo bytes and stores a private cover."""
        first = await upload_photo(client, _RED)
        second = await upload_photo(client, _BLUE)
        project_id = await _project(client, first["id"])

        started = await _generate(client, project_id, [first["id"], second["id"]])

        assert started["status"] == "pending"
        job = editor.jobs[0]
        assert job.prompt == f"direction: {_PROMPT}"
        assert job.project_id == project_id
        assert [p.mime_type for p in job.photos] == ["image/png", "image/png"]
        assert all(p.content.startswith(b"\x89PNG") for p in job.photos)
        listed = await client.get(f"/api/carousels/{project_id}/cover-generations")
        body = listed.json()
        assert body["carousel_used"] == 1
        assert body["carousel_cap"] == 4
        assert body["month_used"] == 1
        assert body["month_cap"] == 40
        generation = body["generations"][0]
        assert generation["status"] == "succeeded"
        assert generation["asset_id"] in await _role_cover_assets()
        image = await client.get(
            f"/api/carousels/creator-assets/{generation['asset_id']}/image"
        )
        assert image.status_code == 200
        with Image.open(BytesIO(image.content)) as stored:
            assert stored.size == (1080, 1350)
        library = await client.get("/api/carousels/creator-assets?role=hook")
        library_ids = {item["id"] for item in library.json()["items"]}
        assert generation["asset_id"] not in library_ids

    async def test_generated_cover_is_an_option_and_can_be_picked(
        self,
        client: AsyncClient,
        asset_dirs: Path,
        editor: _FakeEditor,
        renders: list[str],
    ) -> None:
        """Scenario: The generated cover is a cover option and can be picked."""
        photo = await upload_photo(client, _RED)
        project_id = await _project(client, photo["id"])
        await _generate(client, project_id, [photo["id"]])
        listed = await client.get(f"/api/carousels/{project_id}/cover-generations")
        asset_id = listed.json()["generations"][0]["asset_id"]

        options = await client.get(f"/api/carousels/{project_id}/cover-options")

        found = [
            (o["asset_id"], o["source"], o["kind"]) for o in options.json()["options"]
        ]
        assert found == [
            (photo["id"], "library", ""),
            (asset_id, "generated", "ai_image"),
        ]
        picked = await client.put(
            f"/api/carousels/{project_id}/cover",
            json={"asset_id": asset_id, "expected_version": 4},
        )
        assert picked.status_code == 200, picked.text
        assert picked.json()["current_asset_id"] == asset_id
        assert renders == [project_id]
        cover = await _slide_cover(project_id)
        assert cover["asset_id"] == asset_id
        assert cover["kind"] == "ai_image"

    async def test_confirmation_is_required(
        self, client: AsyncClient, asset_dirs: Path, editor: _FakeEditor
    ) -> None:
        """Scenario: Generation needs an explicit confirmation."""
        photo = await upload_photo(client, _RED)
        project_id = await _project(client, photo["id"])

        response = await client.post(
            f"/api/carousels/{project_id}/cover-generations",
            json=_body([photo["id"]], confirmed=False),
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "cover_generation_not_confirmed"
        assert await _generation_rows() == []
        assert editor.jobs == []

    async def test_only_the_owner_can_generate(
        self, client: AsyncClient, asset_dirs: Path, editor: _FakeEditor
    ) -> None:
        """Scenario: Only the carousel's owner can generate."""
        photo = await upload_photo(client, _RED)
        project_id = await _project(client, photo["id"])
        admin = await create_test_user(f"{uuid4().hex}@x.test", UserRole.ADMIN)

        posted = await client.post(
            f"/api/carousels/{project_id}/cover-generations",
            json=_body([photo["id"]]),
            headers=auth_headers_for(admin),
        )
        listed = await client.get(
            f"/api/carousels/{project_id}/cover-generations",
            headers=auth_headers_for(admin),
        )

        assert posted.status_code == 403
        assert posted.json()["detail"] == "cover_generation_not_owner"
        assert listed.status_code == 403

    async def test_another_owners_photo_is_refused(
        self, client: AsyncClient, asset_dirs: Path, editor: _FakeEditor
    ) -> None:
        """Scenario: Another owner's photo cannot be sent."""
        photo = await upload_photo(client, _RED)
        project_id = await _project(client, photo["id"])
        other = await create_test_user(f"{uuid4().hex}@x.test", UserRole.EDITOR)
        theirs = await upload_photo(client, _BLUE, headers=auth_headers_for(other))

        response = await client.post(
            f"/api/carousels/{project_id}/cover-generations",
            json=_body([theirs["id"]]),
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "cover_generation_photo_not_allowed"

    async def test_radar_carousel_is_refused(
        self, client: AsyncClient, asset_dirs: Path, editor: _FakeEditor
    ) -> None:
        """Scenario: A Radar IA carousel cannot generate a cover."""
        photo = await upload_photo(client, _RED)
        project_id = await _project(client, None, mode="news_analysis")

        response = await client.post(
            f"/api/carousels/{project_id}/cover-generations", json=_body([photo["id"]])
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "cover_pick_not_pov"

    async def test_unknown_carousel_is_404(
        self, client: AsyncClient, editor: _FakeEditor
    ) -> None:
        """Scenario: Only the carousel's owner can generate."""
        response = await client.get(f"/api/carousels/{uuid4()}/cover-generations")
        assert response.status_code == 404


@pytest.mark.integration
class TestFailures:
    async def test_bridge_failure_leaves_no_asset_and_is_free(
        self, client: AsyncClient, asset_dirs: Path, editor: _FakeEditor
    ) -> None:
        """Scenario: A bridge failure leaves no asset and can be retried."""
        editor.error = RuntimeError("Grok Bot image job x expired after 600s")
        photo = await upload_photo(client, _RED)
        project_id = await _project(client, photo["id"])

        await _generate(client, project_id, [photo["id"]])

        body = (
            await client.get(f"/api/carousels/{project_id}/cover-generations")
        ).json()
        assert body["generations"][0]["status"] == "failed"
        assert body["generations"][0]["error_code"] == "cover_generation_bridge_failed"
        assert body["generations"][0]["asset_id"] is None
        assert body["carousel_used"] == 0
        assert body["month_used"] == 0
        assert await _role_cover_assets() == []
        editor.error = None
        retried = await _generate(client, project_id, [photo["id"]])
        assert retried["status"] == "pending"

    async def test_unusable_image_leaves_no_asset(
        self, client: AsyncClient, asset_dirs: Path, editor: _FakeEditor
    ) -> None:
        """Scenario: An unusable image leaves no asset."""
        editor.image = _cover_png((600, 750))
        photo = await upload_photo(client, _RED)
        project_id = await _project(client, photo["id"])

        await _generate(client, project_id, [photo["id"]])

        rows = await _generation_rows(project_id)
        assert rows[0]["status"] == "failed"
        assert rows[0]["error_code"] == "cover_generation_invalid_image"
        assert await _role_cover_assets() == []

    async def test_bridge_not_configured_is_503(
        self, client: AsyncClient, asset_dirs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: The bridge is not configured."""
        from rag_backend.infrastructure.config.settings import get_settings

        monkeypatch.setenv("GROKBOT_IMAGE_WEBHOOK_URL", "")
        get_settings.cache_clear()
        photo = await upload_photo(client, _RED)
        project_id = await _project(client, photo["id"])

        response = await client.post(
            f"/api/carousels/{project_id}/cover-generations", json=_body([photo["id"]])
        )

        assert response.status_code == 503
        assert response.json()["detail"] == "cover_generation_unavailable"
        assert await _generation_rows() == []

    async def test_lost_run_is_reported_as_interrupted(
        self, client: AsyncClient, asset_dirs: Path, editor: _FakeEditor
    ) -> None:
        """Scenario: A run lost to a restart is reported as interrupted."""
        photo = await upload_photo(client, _RED)
        project_id = await _project(client, photo["id"])
        old = datetime.now(UTC) - timedelta(hours=1)
        await _insert_rows(project_id, [("pending", old)])

        body = (
            await client.get(f"/api/carousels/{project_id}/cover-generations")
        ).json()

        assert body["generations"][0]["status"] == "failed"
        assert body["generations"][0]["error_code"] == "cover_generation_interrupted"


@pytest.mark.integration
class TestCaps:
    async def test_one_pending_generation_at_a_time(
        self, client: AsyncClient, asset_dirs: Path, editor: _FakeEditor
    ) -> None:
        """Scenario: One generation at a time per carousel."""
        photo = await upload_photo(client, _RED)
        project_id = await _project(client, photo["id"])
        await _insert_rows(project_id, [("pending", datetime.now(UTC))])

        response = await client.post(
            f"/api/carousels/{project_id}/cover-generations", json=_body([photo["id"]])
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "cover_generation_in_progress"

    async def test_per_carousel_cap_is_four(
        self, client: AsyncClient, asset_dirs: Path, editor: _FakeEditor
    ) -> None:
        """Scenario: The per-carousel cap is four."""
        photo = await upload_photo(client, _RED)
        project_id = await _project(client, photo["id"])
        now = datetime.now(UTC)
        await _insert_rows(project_id, [("succeeded", now)] * 4 + [("failed", now)] * 2)

        response = await client.post(
            f"/api/carousels/{project_id}/cover-generations", json=_body([photo["id"]])
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "cover_generation_carousel_cap"

    async def test_monthly_cap_is_forty(
        self, client: AsyncClient, asset_dirs: Path, editor: _FakeEditor
    ) -> None:
        """Scenario: The monthly cap is forty."""
        photo = await upload_photo(client, _RED)
        project_id = await _project(client, photo["id"])
        now = datetime.now(UTC)
        for _ in range(10):
            other = await _project(client, photo["id"])
            await _insert_rows(other, [("succeeded", now)] * 4)
        last_month = now.replace(day=1) - timedelta(days=1)
        await _insert_rows(project_id, [("failed", now), ("succeeded", last_month)])

        listed = await client.get(f"/api/carousels/{project_id}/cover-generations")
        response = await client.post(
            f"/api/carousels/{project_id}/cover-generations", json=_body([photo["id"]])
        )

        assert listed.json()["month_used"] == 40
        assert response.status_code == 409
        assert response.json()["detail"] == "cover_generation_monthly_cap"


@pytest.mark.integration
async def test_every_call_is_logged_without_the_prompt(
    client: AsyncClient, asset_dirs: Path, editor: _FakeEditor
) -> None:
    """Scenario: Every call is logged for the budget."""
    photo = await upload_photo(client, _RED)
    project_id = await _project(client, photo["id"])

    with capture_logs() as logs:
        await _generate(client, project_id, [photo["id"]])

    entries = [e for e in logs if e.get("event") == "cover_generation"]
    assert [e["outcome"] for e in entries] == ["started", "succeeded"]
    rows = await _generation_rows(project_id)
    for entry in entries:
        assert entry["project_id"] == project_id
        assert entry["prompt_sha256"] == rows[0]["prompt_sha256"]
        assert entry["model"] == "gpt-image-2"
        assert entry["cost_usd"] == 0.0
        assert _PROMPT not in str(entry)
    assert len(str(rows[0]["prompt_sha256"])) == 64
