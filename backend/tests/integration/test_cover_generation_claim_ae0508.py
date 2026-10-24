"""Grok cover generation over HTTP: the bridge-slot claim and the attempt ceiling.

Feature: Generate a slide-1 cover from library photos with Grok
(tests/features/cover_generation_ae0508.feature). The real app over an
in-memory SQLite database with a fake image bridge editor that claims the
generation once its slot is free, as the real bridge does.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from httpx import AsyncClient

from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.modules.editorial.infrastructure.cover_generations import (
    SqlCoverGenerationRepository,
)
from tests.integration.cover_generation_support import (
    RED,
    FakeEditor,
    generation_rows,
    insert_rows,
    install_fake_editor,
    project,
    request_body,
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
class TestClaim:
    async def test_a_started_job_is_timed_from_its_slot(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: A queued job is timed from its bridge slot, not its creation."""
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])
        now = datetime.now(UTC)
        await insert_rows(project_id, [("pending", now - timedelta(hours=1))], now)

        body = (
            await client.get(f"/api/carousels/{project_id}/cover-generations")
        ).json()

        assert body["generations"][0]["status"] == "pending"

    async def test_a_reaped_queued_row_cannot_be_claimed(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: A queued job whose row was failed meanwhile sends nothing."""
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])
        old = datetime.now(UTC) - timedelta(hours=1)
        (row_id,) = await insert_rows(project_id, [("pending", old)])
        await client.get(f"/api/carousels/{project_id}/cover-generations")

        async with get_session_maker()() as session:
            claimed = await SqlCoverGenerationRepository(session).mark_started(
                UUID(row_id), datetime.now(UTC)
            )

        assert claimed is False
        rows = await generation_rows(project_id)
        assert rows[0]["error_code"] == "cover_generation_interrupted"

    async def test_a_pending_row_is_claimed_once(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: A queued job whose row was failed meanwhile sends nothing."""
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])
        (row_id,) = await insert_rows(project_id, [("pending", datetime.now(UTC))])

        async with get_session_maker()() as session:
            repo = SqlCoverGenerationRepository(session)
            first = await repo.mark_started(UUID(row_id), datetime.now(UTC))
            second = await repo.mark_started(UUID(row_id), datetime.now(UTC))
            await session.commit()

        assert (first, second) == (True, False)


@pytest.mark.integration
class TestAttemptCeiling:
    async def test_twelve_attempts_block_the_carousel(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: Failed attempts are free up to a hard attempt ceiling."""
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])
        await insert_rows(project_id, [("failed", datetime.now(UTC))] * 12)

        listed = await client.get(f"/api/carousels/{project_id}/cover-generations")
        response = await client.post(
            f"/api/carousels/{project_id}/cover-generations",
            json=request_body([photo["id"]]),
        )

        body = listed.json()
        assert body["carousel_used"] == 0
        assert (body["carousel_attempts"], body["carousel_attempt_cap"]) == (12, 12)
        assert body["month_attempt_cap"] == 120
        assert response.status_code == 409
        assert response.json()["detail"] == "cover_generation_carousel_attempts"
        assert editor.jobs == []

    async def test_a_hundred_twenty_attempts_block_the_month(
        self, client: AsyncClient, asset_dirs: Path, editor: FakeEditor
    ) -> None:
        """Scenario: Failed attempts are free up to a hard attempt ceiling."""
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])
        now = datetime.now(UTC)
        for _ in range(10):
            other = await project(client, photo["id"])
            await insert_rows(other, [("failed", now)] * 12)

        response = await client.post(
            f"/api/carousels/{project_id}/cover-generations",
            json=request_body([photo["id"]]),
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "cover_generation_monthly_attempts"
