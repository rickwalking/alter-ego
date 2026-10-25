"""Grok cover generation from a text prompt alone, over HTTP.

Feature: Generate a slide-1 cover from a text prompt alone
(tests/features/cover_generation_text_ae0551.feature). The real app over an
in-memory SQLite database with a fake image bridge editor.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient
from structlog.testing import capture_logs

from rag_backend.agents.cover_generation_prompts import (
    cover_edit_prompt,
    cover_text_prompt,
)
from rag_backend.domain.models import UserRole
from tests.integration.conftest import auth_headers_for, create_test_user
from tests.integration.cover_generation_support import (
    BLUE,
    PROMPT,
    RED,
    FakeEditor,
    generate,
    generation_rows,
    insert_rows,
    install_fake_editor,
    project,
    request_body,
    role_cover_assets,
)
from tests.integration.hook_photo_support import upload_photo

_PATH = "/api/carousels/{}/cover-generations"


async def _carousel(client: AsyncClient) -> str:
    """A finished POV carousel of the caller (its slide 1 needs a library photo)."""
    photo = await upload_photo(client, RED)
    return await project(client, photo["id"])


@pytest.fixture(autouse=True)
def _fresh_limiter() -> Iterator[None]:
    from rag_backend.api.middleware.rate_limiting import limiter

    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def editor(monkeypatch: pytest.MonkeyPatch) -> FakeEditor:
    return install_fake_editor(monkeypatch)


@pytest.mark.integration
class TestTextOnly:
    async def test_no_photo_generation_runs_a_text_only_job(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: A confirmed generation without photos runs a text-only job."""
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])

        with capture_logs() as logs:
            started = await generate(client, project_id, [])

        assert started["status"] == "pending"
        assert editor.renderers == [cover_text_prompt]
        job = editor.jobs[0]
        assert job.photo_count == 0
        assert str(job.job_id) == started["id"]
        rows = await generation_rows(project_id)
        assert [(r["photo_count"], r["photo_ids"]) for r in rows] == [(0, [])]
        listed = await client.get(_PATH.format(project_id))
        generation = listed.json()["generations"][0]
        assert generation["status"] == "succeeded"
        assert generation["asset_id"] in await role_cover_assets()
        options = await client.get(f"/api/carousels/{project_id}/cover-options")
        assert (generation["asset_id"], "generated", "ai_image") in [
            (o["asset_id"], o["source"], o["kind"]) for o in options.json()["options"]
        ]
        entries = [e for e in logs if e.get("event") == "cover_generation"]
        assert [e["outcome"] for e in entries] == ["started", "succeeded"]
        assert {e["photo_count"] for e in entries} == {0}
        assert all(PROMPT not in str(e) for e in entries)

    async def test_photo_ids_may_be_absent(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: The photo ids may be absent."""
        project_id = await _carousel(client)

        response = await client.post(
            _PATH.format(project_id), json={"prompt": PROMPT, "confirmed": True}
        )

        assert response.status_code == 202, response.text
        assert response.json()["status"] == "pending"

    async def test_with_photos_the_edit_prompt_is_kept(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: A confirmed generation without photos runs a text-only job."""
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])

        await generate(client, project_id, [photo["id"]])

        assert editor.renderers == [cover_edit_prompt]
        assert editor.jobs[0].photo_count == 1


@pytest.mark.integration
class TestPhotoChecks:
    async def test_more_than_three_ids_are_refused(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: Photo ids are still checked."""
        project_id = await _carousel(client)
        ids = [str(uuid4()) for _ in range(4)]

        response = await client.post(_PATH.format(project_id), json=request_body(ids))

        assert response.status_code == 422
        assert await generation_rows() == []
        assert editor.jobs == []

    async def test_a_foreign_photo_is_refused(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: Photo ids are still checked."""
        project_id = await _carousel(client)
        other = await create_test_user(f"{uuid4().hex}@x.test", UserRole.EDITOR)
        theirs = await upload_photo(client, BLUE, headers=auth_headers_for(other))

        response = await client.post(
            _PATH.format(project_id), json=request_body([theirs["id"]])
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "cover_generation_photo_not_allowed"
        assert await generation_rows() == []


@pytest.mark.integration
class TestSameRules:
    @pytest.mark.parametrize(
        ("rows", "code"),
        [
            (["pending"], "cover_generation_in_progress"),
            (["succeeded"] * 4, "cover_generation_carousel_cap"),
            (["failed"] * 12, "cover_generation_carousel_attempts"),
        ],
    )
    async def test_caps_and_lock_refuse_a_text_only_generation(
        self,
        client: AsyncClient,
        asset_dirs: Path,
        editor: FakeEditor,
        rows: list[str],
        code: str,
    ) -> None:
        """Scenario: A text-only generation follows the same caps and lock."""
        project_id = await _carousel(client)
        now = datetime.now(UTC)
        await insert_rows(project_id, [(status, now) for status in rows], now)

        response = await client.post(_PATH.format(project_id), json=request_body([]))

        assert response.status_code == 409
        assert response.json()["detail"] == code
        assert editor.jobs == []

    async def test_confirmation_is_still_required(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: A text-only generation follows the same caps and lock."""
        project_id = await _carousel(client)

        response = await client.post(
            _PATH.format(project_id), json=request_body([], confirmed=False)
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "cover_generation_not_confirmed"
        assert await generation_rows() == []
