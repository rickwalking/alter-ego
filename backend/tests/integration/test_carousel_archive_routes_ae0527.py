"""The owner archives and restores a carousel; the workflow board follows."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

from rag_backend.domain.constants.carousel_archive import (
    ERR_ARCHIVE_IN_PROGRESS,
    ERR_ARCHIVE_PUBLISHED,
)
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_PUBLISHED,
    PHASE_STATUS_IN_PROGRESS,
)
from tests.integration.carousel_copy_support import CopyEnv, copy_env_context

_BOARD = "/api/workflow-board"


@pytest.fixture(autouse=True)
def _fresh_rate_limits() -> None:
    from rag_backend.api.middleware.rate_limiting import limiter

    limiter.reset()


@pytest_asyncio.fixture
async def env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[CopyEnv]:
    async with copy_env_context(tmp_path, monkeypatch) as built:
        yield built


def _archive(project_id: str) -> str:
    return f"/api/carousels/{project_id}/archive"


def _restore(project_id: str) -> str:
    return f"/api/carousels/{project_id}/restore"


async def _board_ids(client: AsyncClient, *, archived: bool = False) -> set[str]:
    params = {"archived": "true"} if archived else {}
    response = await client.get(_BOARD, params=params)
    assert response.status_code == 200
    return {
        card["id"] for column in response.json()["columns"] for card in column["cards"]
    }


@pytest.mark.asyncio
async def test_owner_archives_a_stale_carousel(env: CopyEnv) -> None:
    """Scenario: The owner archives a stale carousel"""
    project_id = await env.seed_carousel()
    async with env.client_for(env.owner) as client:
        assert project_id in await _board_ids(client)
        response = await client.post(_archive(project_id))
        active = await _board_ids(client)
        archived = await _board_ids(client, archived=True)

    assert response.status_code == 200
    assert response.json()["archived"] is True
    assert response.json()["archived_at"] is not None
    assert project_id not in active
    assert archived == {project_id}


@pytest.mark.asyncio
async def test_archiving_twice_keeps_the_first_time(env: CopyEnv) -> None:
    """Scenario: Archiving twice keeps the first archive time"""
    project_id = await env.seed_carousel()
    async with env.client_for(env.owner) as client:
        first = await client.post(_archive(project_id))
        second = await client.post(_archive(project_id))

    assert second.status_code == 200
    assert second.json()["archived_at"] == first.json()["archived_at"]


@pytest.mark.asyncio
async def test_owner_restores_an_archived_carousel(env: CopyEnv) -> None:
    """Scenario: The owner restores an archived carousel"""
    project_id = await env.seed_carousel()
    async with env.client_for(env.owner) as client:
        await client.post(_archive(project_id))
        restored = await client.post(_restore(project_id))
        again = await client.post(_restore(project_id))
        active = await _board_ids(client)
        archived = await _board_ids(client, archived=True)

    assert restored.status_code == 200
    assert restored.json() == {"id": project_id, "archived": False, "archived_at": None}
    assert again.status_code == 200
    assert project_id in active
    assert archived == set()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("values", "detail"),
    [
        ({"phase_status": PHASE_STATUS_IN_PROGRESS}, ERR_ARCHIVE_IN_PROGRESS),
        ({"current_phase": PHASE_PUBLISHED}, ERR_ARCHIVE_PUBLISHED),
    ],
)
async def test_in_progress_and_published_carousels_are_refused(
    env: CopyEnv, values: dict[str, object], detail: str
) -> None:
    """Scenario: A carousel in progress cannot be archived

    Scenario: A published carousel cannot be archived
    """
    project_id = await env.seed_carousel()
    await env.set_project(project_id, values)
    async with env.client_for(env.owner) as client:
        response = await client.post(_archive(project_id))
        archived = await _board_ids(client, archived=True)

    assert response.status_code == 409
    assert response.json()["detail"] == detail
    assert archived == set()


@pytest.mark.asyncio
async def test_someone_elses_carousel_is_refused_but_an_admin_may(env: CopyEnv) -> None:
    """Scenario: Someone else's carousel cannot be archived or restored"""
    project_id = await env.seed_carousel()
    async with env.client_for(env.other) as other:
        archive = await other.post(_archive(project_id))
        restore = await other.post(_restore(project_id))
    async with env.client_for(env.admin) as admin:
        archived = await admin.post(_archive(project_id))
        restored = await admin.post(_restore(project_id))

    assert archive.status_code == 403
    assert restore.status_code == 403
    assert archived.status_code == 200
    assert archived.json()["archived"] is True
    assert restored.status_code == 200
    assert restored.json()["archived"] is False


@pytest.mark.asyncio
async def test_unknown_carousel_is_not_found(env: CopyEnv) -> None:
    """Scenario: An unknown carousel cannot be archived"""
    async with env.client_for(env.owner) as client:
        archive = await client.post(_archive(str(uuid4())))
        restore = await client.post(_restore(str(uuid4())))

    assert archive.status_code == 404
    assert restore.status_code == 404
