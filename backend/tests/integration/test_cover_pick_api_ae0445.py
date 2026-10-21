"""Publish-step slide-1 cover picker over HTTP (AE-0445).

Gherkin: tests/features/carousel_cover_pick_ae0445.feature
  Scenario: The options are the owner's library photos, the current one marked
  Scenario: The GrokBot cover offer of the autopilot run is an option too
  Scenario: A library photo whose file is gone is not offered
  Scenario: A Radar IA carousel has no cover options
  Scenario: Choosing another library photo re-renders slide 1 from it
  Scenario: Choosing a library photo replaces a GrokBot cover chosen on Telegram
  Scenario: Choosing the GrokBot offer stores it as the slide-1 cover
  Scenario: A stale lock version is a conflict and writes nothing
  Scenario: An active workflow run is a conflict
  Scenario Outline: Refused choices
  Scenario: Another user cannot change the cover
  Scenario: A failed re-render is reported, the choice stays stored

SQLite has no advisory lock (the project lock is a no-op there) but the
lock-version CAS is real. The republish renderer and the GrokBot offer
source are stubbed.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from rag_backend.api.routes.carousels import cover_pick as cover_pick_route
from rag_backend.domain.models import UserRole
from rag_backend.domain.models.slide_cover import SlideCover
from rag_backend.modules.editorial.infrastructure import carousel_owner_autofix
from tests.integration.conftest import auth_headers_for, create_test_user
from tests.integration.hook_photo_support import upload_photo

_THESIS = "A IA escreve código. Quem decide ainda é você."
_RED = (200, 10, 10, 0)
_BLUE = (10, 10, 200, 0)


class _Offers:
    """A fixed GrokBot offer (or none) for every project."""

    def __init__(self, cover: SlideCover | None) -> None:
        self.cover = cover

    async def offer(self, project_id: str) -> SlideCover | None:
        del project_id
        return self.cover


@pytest.fixture(autouse=True)
def _fresh_limiter() -> Iterator[None]:
    """The in-memory limiter is process-wide; these tests upload a lot."""
    from rag_backend.api.middleware.rate_limiting import limiter

    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def offers(monkeypatch: pytest.MonkeyPatch) -> _Offers:
    stub = _Offers(None)
    monkeypatch.setattr(cover_pick_route, "project_cover_offer", lambda _db: stub)
    return stub


@pytest.fixture
def renders(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    calls: list[str] = []

    async def _render(_self: object, project_id: str) -> tuple[str, ...]:
        calls.append(project_id)
        return ()

    monkeypatch.setattr(carousel_owner_autofix.RepublishRenderer, "render", _render)
    yield calls


async def _project(client: AsyncClient, photo_id: object, mode: str = "pov") -> str:
    body: dict[str, object] = {"topic": "T", "audience": "Devs", "niche": "IA"}
    if mode != "news_analysis":
        body |= {"content_mode": mode, "pov_thesis": _THESIS, "hook_asset_id": photo_id}
    created = await client.post("/api/carousels", json=body)
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


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


async def _row(project_id: str) -> dict[str, object]:
    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.carousel import (
        CarouselProjectModel,
    )

    async with get_session_maker()() as session:
        model = await session.get(CarouselProjectModel, project_id)
        assert model is not None
        return {
            "hook_asset_id": model.hook_asset_id,
            "slide_cover": model.slide_cover,
            "lock_version": model.lock_version,
            "output_dir": model.output_dir,
        }


async def _finished(client: AsyncClient, photo_id: object, mode: str = "pov") -> str:
    project_id = await _project(client, photo_id, mode)
    await _set(
        project_id, status="completed", phase_status="awaiting_human", lock_version=4
    )
    return project_id


def _stored(asset_dirs: Path, body: dict[str, object]) -> Path:
    sha = str(body["content_sha256"])
    return asset_dirs / "assets" / f"{sha}.webp"


@pytest.mark.integration
class TestCoverOptions:
    async def test_library_photos_with_the_current_marked(
        self, client: AsyncClient, asset_dirs: Path, offers: _Offers
    ) -> None:
        first = await upload_photo(client, _RED)
        second = await upload_photo(client, _BLUE)
        project_id = await _finished(client, first["id"])

        response = await client.get(f"/api/carousels/{project_id}/cover-options")

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["current_asset_id"] == first["id"]
        ids = {(o["asset_id"], o["source"]) for o in body["options"]}
        assert ids == {(first["id"], "library"), (second["id"], "library")}

    async def test_offer_is_listed_and_a_gone_file_is_not(
        self, client: AsyncClient, asset_dirs: Path, offers: _Offers
    ) -> None:
        first = await upload_photo(client, _RED)
        second = await upload_photo(client, _BLUE)
        project_id = await _finished(client, first["id"])
        _stored(asset_dirs, second).unlink()
        grok = uuid4()
        offers.cover = SlideCover(asset_id=grok, kind="ai_image", staged_path="g.webp")

        body = (await client.get(f"/api/carousels/{project_id}/cover-options")).json()

        options = [(o["asset_id"], o["source"], o["kind"]) for o in body["options"]]
        assert options == [
            (first["id"], "library", ""),
            (str(grok), "offer", "ai_image"),
        ]

    async def test_radar_carousel_is_refused(
        self, client: AsyncClient, asset_dirs: Path, offers: _Offers
    ) -> None:
        project_id = await _finished(client, None, mode="news_analysis")
        response = await client.get(f"/api/carousels/{project_id}/cover-options")
        assert response.status_code == 422
        assert response.json()["detail"] == "cover_pick_not_pov"

    async def test_unknown_project_is_404(
        self, client: AsyncClient, offers: _Offers
    ) -> None:
        response = await client.get(f"/api/carousels/{uuid4()}/cover-options")
        assert response.status_code == 404


@pytest.mark.integration
class TestCoverPick:
    async def test_library_photo_is_staged_bound_and_re_rendered(
        self,
        client: AsyncClient,
        asset_dirs: Path,
        offers: _Offers,
        renders: list[str],
    ) -> None:
        first = await upload_photo(client, _RED)
        second = await upload_photo(client, _BLUE)
        project_id = await _finished(client, first["id"])
        grok = SlideCover(asset_id=uuid4(), kind="ai_image", staged_path="g.webp")
        await _set(project_id, slide_cover=grok.to_row())

        response = await client.put(
            f"/api/carousels/{project_id}/cover",
            json={"asset_id": second["id"], "expected_version": 4},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert (body["status"], body["current_asset_id"]) == ("switched", second["id"])
        row = await _row(project_id)
        assert row["hook_asset_id"] == second["id"]
        assert row["slide_cover"] is None
        assert row["lock_version"] == 5
        assert renders == [project_id]
        root = asset_dirs / "output" / project_id
        assert (root / str(second["relative_path"])).is_file()

    async def test_offer_is_stored_as_the_slide_cover(
        self,
        client: AsyncClient,
        asset_dirs: Path,
        offers: _Offers,
        renders: list[str],
    ) -> None:
        first = await upload_photo(client, _RED)
        # The offer's creator asset: any stored photo of the owner will do.
        grok_photo = await upload_photo(client, _BLUE)
        project_id = await _finished(client, first["id"])
        offers.cover = SlideCover(
            asset_id=UUID(str(grok_photo["id"])),
            kind="ai_image",
            staged_path=str(grok_photo["relative_path"]),
        )

        response = await client.put(
            f"/api/carousels/{project_id}/cover",
            json={"asset_id": str(offers.cover.asset_id), "expected_version": 4},
        )

        assert response.status_code == 200, response.text
        row = await _row(project_id)
        assert row["slide_cover"] == offers.cover.to_row()
        assert row["hook_asset_id"] == first["id"]
        assert renders == [project_id]

    async def test_stale_version_is_409_and_writes_nothing(
        self,
        client: AsyncClient,
        asset_dirs: Path,
        offers: _Offers,
        renders: list[str],
    ) -> None:
        first = await upload_photo(client, _RED)
        second = await upload_photo(client, _BLUE)
        project_id = await _finished(client, first["id"])

        response = await client.put(
            f"/api/carousels/{project_id}/cover",
            json={"asset_id": second["id"], "expected_version": 3},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "version_conflict"
        row = await _row(project_id)
        assert (row["hook_asset_id"], row["lock_version"]) == (first["id"], 4)
        assert renders == []

    async def test_active_run_is_409(
        self, client: AsyncClient, asset_dirs: Path, offers: _Offers
    ) -> None:
        first = await upload_photo(client, _RED)
        second = await upload_photo(client, _BLUE)
        project_id = await _finished(client, first["id"])
        await _set(project_id, phase_status="in_progress")

        response = await client.put(
            f"/api/carousels/{project_id}/cover",
            json={"asset_id": second["id"], "expected_version": 4},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "resume_already_in_progress"

    @pytest.mark.parametrize(
        ("mode", "status", "asset", "code"),
        [
            ("news_analysis", "completed", "second", "cover_pick_not_pov"),
            ("pov_news", "drafting", "second", "cover_pick_not_completed"),
            ("pov", "completed", "foreign", "cover_pick_asset_not_allowed"),
            ("pov", "completed", "unknown", "cover_pick_asset_not_allowed"),
            ("pov", "completed", "gone", "cover_pick_asset_not_allowed"),
        ],
    )
    async def test_refused_choices_write_nothing(
        self,
        client: AsyncClient,
        asset_dirs: Path,
        offers: _Offers,
        renders: list[str],
        mode: str,
        status: str,
        asset: str,
        code: str,
    ) -> None:
        first = await upload_photo(client, _RED)
        second = await upload_photo(client, _BLUE)
        other = await create_test_user(f"{uuid4().hex}@x.test", UserRole.EDITOR)
        foreign = await upload_photo(client, (1, 2, 3, 0), auth_headers_for(other))
        photo = None if mode == "news_analysis" else first["id"]
        project_id = await _project(client, photo, mode)
        await _set(project_id, status=status, phase_status="awaiting_human")
        if asset == "gone":
            _stored(asset_dirs, second).unlink()
        chosen = {
            "second": second["id"],
            "gone": second["id"],
            "foreign": foreign["id"],
            "unknown": str(uuid4()),
        }[asset]

        response = await client.put(
            f"/api/carousels/{project_id}/cover",
            json={"asset_id": chosen, "expected_version": 1},
        )

        assert response.status_code == 422, response.text
        assert response.json()["detail"] == code
        assert (await _row(project_id))["hook_asset_id"] == photo
        assert renders == []

    async def test_another_editor_is_403(
        self, client: AsyncClient, asset_dirs: Path, offers: _Offers
    ) -> None:
        first = await upload_photo(client, _RED)
        project_id = await _finished(client, first["id"])
        other = await create_test_user(f"{uuid4().hex}@x.test", UserRole.EDITOR)

        response = await client.put(
            f"/api/carousels/{project_id}/cover",
            json={"asset_id": first["id"], "expected_version": 4},
            headers=auth_headers_for(other),
        )

        assert response.status_code == 403

    async def test_failed_render_is_422_and_the_choice_stays(
        self,
        client: AsyncClient,
        asset_dirs: Path,
        offers: _Offers,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async def _broken(_self: object, project_id: str) -> tuple[str, ...]:
            del project_id
            return ("render failed",)

        monkeypatch.setattr(carousel_owner_autofix.RepublishRenderer, "render", _broken)
        first = await upload_photo(client, _RED)
        second = await upload_photo(client, _BLUE)
        project_id = await _finished(client, first["id"])

        response = await client.put(
            f"/api/carousels/{project_id}/cover",
            json={"asset_id": second["id"], "expected_version": 4},
        )

        assert response.status_code == 422
        assert "render failed" in str(response.json()["detail"])
        assert (await _row(project_id))["hook_asset_id"] == second["id"]
