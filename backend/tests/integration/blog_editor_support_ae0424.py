"""Shared helpers of the AE-0424 blog editor API tests.

Each test gets its own SQLite file (AE-0390 isolation) and clients for an
admin, an editor author and a distinct editor reviewer.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from rag_backend.domain.constants.optimistic_locking import HTTP_HEADER_IF_MATCH
from rag_backend.domain.models import UserRole
from tests.blog_v2_support import v2_content, v2_section
from tests.integration.conftest import auth_headers_for, create_test_user

BLOG_POSTS_URL = "/api/blog-posts"
SEC_1 = "sec_00000000-0000-4000-8000-000000000001"
SEC_2 = "sec_00000000-0000-4000-8000-000000000002"
SEC_3 = "sec_00000000-0000-4000-8000-000000000003"


@dataclass(frozen=True)
class EditorClients:
    """``author`` writes posts; ``reviewer`` is a distinct editor."""

    author: AsyncClient
    reviewer: AsyncClient
    author_id: str
    reviewer_id: str


def _client(app: FastAPI, headers: dict[str, str]) -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test", headers=headers)


@asynccontextmanager
async def editor_clients(tmp_path: Path) -> AsyncIterator[EditorClients]:
    """Author + reviewer clients on a per-test SQLite database."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.api.middleware.rate_limiting import limiter
    from rag_backend.infrastructure.database.config import Base, close_db

    # The in-memory limiter is process-wide: reset it so these request-heavy
    # tests neither trip nor exhaust the budget of the next test file.
    limiter.reset()
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ae0424.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    author = await create_test_user("author@ae0424.test", UserRole.EDITOR)
    reviewer = await create_test_user("reviewer@ae0424.test", UserRole.EDITOR)
    app = create_app()
    async with (
        _client(app, auth_headers_for(author)) as a,
        _client(app, auth_headers_for(reviewer)) as r,
    ):
        yield EditorClients(a, r, str(author.id), str(reviewer.id))
    limiter.reset()
    db_config.c_engine = None
    await close_db()
    await engine.dispose()


def three_sections() -> dict[str, object]:
    """A v2 document with sections sec_1..sec_3."""
    content = v2_content()
    content["sections"] = [
        v2_section("Corpo um", "Um", SEC_1),
        v2_section("Corpo dois", "Dois", SEC_2),
        v2_section("Corpo três", "Três", SEC_3),
    ]
    return content


async def create_post(client: AsyncClient, content: dict[str, object]) -> dict:
    response = await client.post(
        BLOG_POSTS_URL, json={"title": "GPT 5.6 saiu", "content": content}
    )
    assert response.status_code == 201, response.text
    return response.json()


def if_match(post: dict) -> dict[str, str]:
    return {HTTP_HEADER_IF_MATCH: str(post["lock_version"])}


async def put(client: AsyncClient, post: dict, payload: dict) -> Response:
    return await client.put(
        f"{BLOG_POSTS_URL}/{post['id']}", json=payload, headers=if_match(post)
    )


async def get_post(client: AsyncClient, post_id: str) -> dict:
    response = await client.get(f"{BLOG_POSTS_URL}/{post_id}")
    assert response.status_code == 200, response.text
    return response.json()


async def set_fields(post_id: str, **fields: object) -> None:
    """Write row columns directly (state set-up only)."""
    from sqlalchemy import update

    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

    async with get_session_maker()() as session:
        await session.execute(
            update(BlogPostModel).where(BlogPostModel.id == post_id).values(**fields)
        )
        await session.commit()


async def versions(client: AsyncClient, post_id: str) -> list[dict]:
    response = await client.get(f"{BLOG_POSTS_URL}/{post_id}/versions")
    assert response.status_code == 200, response.text
    return response.json()
