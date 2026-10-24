"""Two simultaneous ``POST /cover-generations`` at the last slot, on Postgres.

Feature: Generate a slide-1 cover from library photos with Grok
(tests/features/cover_generation_ae0508.feature). The real app over an
isolated Postgres schema; the bridge editor is a fake. A barrier after the
usage read holds each request until both read (or a timeout), so without the
owner-row lock both would pass. Skipped without a Postgres ``DATABASE_URL``.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

import rag_backend.infrastructure.database.config as db_config
from rag_backend.application.services.carousel.cover_generation_tasks import (
    running_cover_generation_tasks,
)
from rag_backend.domain.models import UserRole
from rag_backend.infrastructure.database.config import Base
from rag_backend.modules.editorial.infrastructure.cover_generations import (
    SqlCoverGenerationRepository,
)
from tests.integration.conftest import auth_headers_for, create_test_user
from tests.integration.cover_generation_support import (
    RED,
    generation_rows,
    insert_rows,
    install_fake_editor,
    project,
    request_body,
)
from tests.integration.hook_photo_support import upload_photo
from tests.integration.pg_schema_support import isolated_schema, requires_postgres

_BARRIER_SECONDS = 0.5


@asynccontextmanager
async def _pg_client() -> AsyncIterator[AsyncClient]:
    """The app over a fresh Postgres schema holding every table.

    Opened inside the test so the asyncpg connections live on its loop.
    """
    from rag_backend.api.app import create_app
    from rag_backend.api.middleware.rate_limiting import limiter

    async with isolated_schema(list(Base.metadata.tables)) as engine:
        previous = db_config.c_engine
        db_config.c_engine = engine
        limiter.reset()
        try:
            user = await create_test_user("owner@pg-race.test", UserRole.EDITOR)
            transport = ASGITransport(app=create_app())
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
                headers=auth_headers_for(user),
            ) as client:
                yield client
            await asyncio.gather(*running_cover_generation_tasks())
        finally:
            limiter.reset()
            db_config.c_engine = previous


@pytest.fixture
def barrier(monkeypatch: pytest.MonkeyPatch) -> asyncio.Event:
    both = asyncio.Event()
    arrived: list[int] = []
    read = SqlCoverGenerationRepository.count_owner_attempts_since

    async def _paused(
        self: SqlCoverGenerationRepository, owner_id: str, since: datetime
    ) -> int:
        count = await read(self, owner_id, since)
        arrived.append(1)
        if len(arrived) >= 2:
            both.set()
        try:
            await asyncio.wait_for(both.wait(), _BARRIER_SECONDS)
        except TimeoutError:
            return count
        return count

    monkeypatch.setattr(
        SqlCoverGenerationRepository, "count_owner_attempts_since", _paused
    )
    return both


@requires_postgres
@pytest.mark.usefixtures("barrier")
async def test_two_posts_at_three_of_four_get_one_202(
    asset_dirs: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Two simultaneous starts at the last slot let exactly one through."""
    install_fake_editor(monkeypatch)
    async with _pg_client() as client:
        photo = await upload_photo(client, RED)
        project_id = await project(client, photo["id"])
        await insert_rows(project_id, [("succeeded", datetime.now(UTC))] * 3)
        url = f"/api/carousels/{project_id}/cover-generations"

        responses = await asyncio.gather(
            client.post(url, json=request_body([photo["id"]])),
            client.post(url, json=request_body([photo["id"]])),
        )
        await asyncio.gather(*running_cover_generation_tasks())
        rows = await generation_rows(project_id)

    assert sorted(r.status_code for r in responses) == [202, 409]
    refused = next(r for r in responses if r.status_code == 409)
    assert refused.json()["detail"] == "cover_generation_in_progress"
    assert len(rows) == 4
    assert asset_dirs.exists()
