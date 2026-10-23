"""Grok cover generation over HTTP: failures, caps and the budget log.

Feature: Generate a slide-1 cover from library photos with Grok
(tests/features/cover_generation_ae0508.feature). The real app over an
in-memory SQLite database with a fake image bridge editor.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from structlog.testing import capture_logs

from tests.integration.cover_generation_support import (
    PROMPT,
    RED,
    FakeEditor,
    cover_png,
    generate,
    generation_rows,
    insert_rows,
    install_fake_editor,
    project,
    request_body,
    role_cover_assets,
)
from tests.integration.hook_photo_support import upload_photo


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
class TestFailures:
    async def test_bridge_failure_leaves_no_asset_and_is_free(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: A bridge failure leaves no asset and can be retried."""
        editor.error = RuntimeError("Grok Bot image job x expired after 600s")
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])

        await generate(client, project_id, [photo["id"]])

        body = (
            await client.get(f"/api/carousels/{project_id}/cover-generations")
        ).json()
        assert body["generations"][0]["status"] == "failed"
        assert body["generations"][0]["error_code"] == "cover_generation_bridge_failed"
        assert body["generations"][0]["asset_id"] is None
        assert body["carousel_used"] == 0
        assert body["month_used"] == 0
        assert await role_cover_assets() == []
        editor.error = None
        retried = await generate(client, project_id, [photo["id"]])
        assert retried["status"] == "pending"

    async def test_unusable_image_leaves_no_asset(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: An unusable image leaves no asset."""
        editor.image = cover_png((600, 750))
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])

        await generate(client, project_id, [photo["id"]])

        rows = await generation_rows(project_id)
        assert rows[0]["status"] == "failed"
        assert rows[0]["error_code"] == "cover_generation_invalid_image"
        assert await role_cover_assets() == []

    async def test_bridge_not_configured_is_503(
        self, client: AsyncClient, asset_dirs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: The bridge is not configured."""
        from rag_backend.infrastructure.config.settings import get_settings

        monkeypatch.setenv("GROKBOT_IMAGE_WEBHOOK_URL", "")
        get_settings.cache_clear()
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])

        response = await client.post(
            f"/api/carousels/{project_id}/cover-generations",
            json=request_body([photo["id"]]),
        )

        assert response.status_code == 503
        assert response.json()["detail"] == "cover_generation_unavailable"
        assert await generation_rows() == []

    async def test_lost_run_is_reported_as_interrupted(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: A run lost to a restart is reported as interrupted."""
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])
        old = datetime.now(UTC) - timedelta(hours=1)
        await insert_rows(project_id, [("pending", old)])

        body = (
            await client.get(f"/api/carousels/{project_id}/cover-generations")
        ).json()

        assert body["generations"][0]["status"] == "failed"
        assert body["generations"][0]["error_code"] == "cover_generation_interrupted"


@pytest.mark.integration
class TestCaps:
    async def test_one_pending_generation_at_a_time(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: One generation at a time per carousel."""
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])
        await insert_rows(project_id, [("pending", datetime.now(UTC))])

        response = await client.post(
            f"/api/carousels/{project_id}/cover-generations",
            json=request_body([photo["id"]]),
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "cover_generation_in_progress"

    async def test_per_carousel_cap_is_four(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: The per-carousel cap is four."""
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])
        now = datetime.now(UTC)
        await insert_rows(project_id, [("succeeded", now)] * 4 + [("failed", now)] * 2)

        response = await client.post(
            f"/api/carousels/{project_id}/cover-generations",
            json=request_body([photo["id"]]),
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "cover_generation_carousel_cap"

    async def test_monthly_cap_is_forty(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: The monthly cap is forty."""
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])
        now = datetime.now(UTC)
        for _ in range(10):
            other = await project(client, photo["id"])
            await insert_rows(other, [("succeeded", now)] * 4)
        last_month = now.replace(day=1) - timedelta(days=1)
        await insert_rows(project_id, [("failed", now), ("succeeded", last_month)])

        listed = await client.get(f"/api/carousels/{project_id}/cover-generations")
        response = await client.post(
            f"/api/carousels/{project_id}/cover-generations",
            json=request_body([photo["id"]]),
        )

        assert listed.json()["month_used"] == 40
        assert response.status_code == 409
        assert response.json()["detail"] == "cover_generation_monthly_cap"


@pytest.mark.integration
async def test_every_call_is_logged_without_the_prompt(
    client: AsyncClient, asset_dirs: Path, editor: FakeEditor
) -> None:
    """Scenario: Every call is logged for the budget."""
    photo = await upload_photo(client, RED)
    project_id = await project(client, photo["id"])

    with capture_logs() as logs:
        await generate(client, project_id, [photo["id"]])

    entries = [e for e in logs if e.get("event") == "cover_generation"]
    assert [e["outcome"] for e in entries] == ["started", "succeeded"]
    rows = await generation_rows(project_id)
    for entry in entries:
        assert entry["project_id"] == project_id
        assert entry["prompt_sha256"] == rows[0]["prompt_sha256"]
        assert entry["model"] == "gpt-image-2"
        assert entry["cost_usd"] == 0.0
        assert PROMPT not in str(entry)
    assert len(str(rows[0]["prompt_sha256"])) == 64
