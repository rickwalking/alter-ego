"""API tests for the blog.v2 document contract (AE-0423, ADR-0025).

Feature: backend/tests/features/blog_sections_ae0423.feature
Strict v2 writes, the ``featured_image_url`` cover projection, the publish
guard, the public projection and the strict (fail-closed) read.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.constants.blog_document import (
    ERR_BLOG_DOCUMENT_NOT_V2,
    ERR_BLOG_NOT_PUBLISHABLE,
    ERR_INVALID_BLOG_DOCUMENT,
)
from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.domain.constants.optimistic_locking import HTTP_HEADER_IF_MATCH
from rag_backend.domain.models import UserRole
from tests.blog_v2_support import v2_content, v2_section
from tests.integration.conftest import auth_headers_for, create_test_user

BLOG_POSTS_URL = "/api/blog-posts"
PUBLIC_URL = "/api/public/blog-posts"
SEC_2 = "sec_00000000-0000-4000-8000-000000000002"
SLIDE_IMAGES = "/slide-images/"
QUALITY = {"voice_score": 81.0, "rewrite_passes": 1}


def _image(url: str = "https://cdn.example/x.jpg", alt: str = "Diagrama") -> dict:
    return {
        "url": url,
        "alt": alt,
        "caption": None,
        "source": "generated",
        "prompt": "internal prompt",
        "model": "gpt-image-2",
        "created_at": "2026-10-18T12:00:00Z",
    }


@pytest.fixture
async def admin_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    """Admin client on a per-test SQLite file (see AE-0390)."""
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.database.config import Base, close_db

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ae0423.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine

    admin = await create_test_user("admin@ae0423.test", UserRole.ADMIN)
    transport = ASGITransport(app=create_app())
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=auth_headers_for(admin)
    ) as ac:
        yield ac

    db_config.c_engine = None
    await close_db()
    await engine.dispose()


async def _create(client: AsyncClient, **payload: object) -> dict:
    body = {"title": "GPT 5.6 saiu", **payload}
    response = await client.post(BLOG_POSTS_URL, json=body)
    assert response.status_code == 201, response.text
    return response.json()


async def _put(client: AsyncClient, post: dict, payload: dict):
    return await client.put(
        f"{BLOG_POSTS_URL}/{post['id']}",
        json=payload,
        headers={HTTP_HEADER_IF_MATCH: str(post["lock_version"])},
    )


async def _set_fields(post_id: str, **fields: object) -> None:
    from sqlalchemy import update

    from rag_backend.infrastructure.database.config import get_session_maker
    from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

    async with get_session_maker()() as session:
        await session.execute(
            update(BlogPostModel).where(BlogPostModel.id == post_id).values(**fields)
        )
        await session.commit()


async def _get(client: AsyncClient, post_id: str) -> dict:
    response = await client.get(f"{BLOG_POSTS_URL}/{post_id}")
    assert response.status_code == 200
    return response.json()


class TestStrictWrites:
    async def test_create_without_content_stores_a_v2_document(
        self, admin_client: AsyncClient
    ) -> None:
        post = await _create(admin_client)
        content = post["content"]
        assert content["schema"] == "blog.v2"
        assert len(content["sections"]) == 1
        assert post["featured_image_url"] is None

    # Scenario: A non-v2 write shape is rejected, never coerced
    async def test_create_with_legacy_content_is_422(
        self, admin_client: AsyncClient
    ) -> None:
        response = await admin_client.post(
            BLOG_POSTS_URL, json={"title": "x", "content": {"markdown": "## A\n\nb"}}
        )
        assert response.status_code == 422
        assert response.json()["detail"] == ERR_BLOG_DOCUMENT_NOT_V2

    # Scenario: Writes remain strict while the read fail-safe is active
    async def test_put_legacy_shape_is_422_and_nothing_persisted(
        self, admin_client: AsyncClient
    ) -> None:
        post = await _create(admin_client, content=v2_content("Original"))
        response = await _put(admin_client, post, {"content": {"markdown": "x"}})
        assert response.status_code == 422
        assert response.json()["detail"] == ERR_BLOG_DOCUMENT_NOT_V2
        stored = await _get(admin_client, post["id"])
        assert stored["content"]["sections"][0]["body_md"] == "Original"
        assert stored["lock_version"] == post["lock_version"]

    # Scenario: A section image with an empty alt is rejected on write
    async def test_put_empty_alt_is_422(self, admin_client: AsyncClient) -> None:
        post = await _create(admin_client, content=v2_content("Body"))
        content = v2_content("Body")
        content["sections"] = [{**v2_section("Body"), "image": _image(alt="")}]
        response = await _put(admin_client, post, {"content": content})
        assert response.status_code == 422
        assert response.json()["detail"].startswith(ERR_INVALID_BLOG_DOCUMENT)
        stored = await _get(admin_client, post["id"])
        assert stored["content"]["sections"][0]["image"] is None

    # Scenario: Duplicate section ids are rejected
    async def test_put_duplicate_section_ids_is_422(
        self, admin_client: AsyncClient
    ) -> None:
        post = await _create(admin_client, content=v2_content("Body"))
        content = v2_content("Body")
        content["sections"] = [v2_section("a"), v2_section("b")]
        response = await _put(admin_client, post, {"content": content})
        assert response.status_code == 422

    # Scenario: An in-progress draft may have zero sections and a null quality
    async def test_zero_sections_allowed_only_while_generating(
        self, admin_client: AsyncClient
    ) -> None:
        post = await _create(admin_client, content=v2_content("Body"))
        empty = {**v2_content(), "sections": []}
        assert (await _put(admin_client, post, {"content": empty})).status_code == 422
        await _set_fields(
            post["id"], ai_generation_metadata={"generation": {"status": "in_progress"}}
        )
        response = await _put(admin_client, post, {"content": empty})
        assert response.status_code == 200, response.text
        assert response.json()["content"]["sections"] == []


class TestCoverProjection:
    # Scenario: featured_image_url tracks cover.url on save
    async def test_featured_image_url_follows_the_cover(
        self, admin_client: AsyncClient
    ) -> None:
        post = await _create(admin_client, content=v2_content("Body"))
        content = {**v2_content("Body"), "cover": _image("https://cdn.example/c.jpg")}
        response = await _put(
            admin_client,
            post,
            {"content": content, "featured_image_url": "https://evil.example/x"},
        )
        assert response.status_code == 200, response.text
        updated = response.json()
        assert updated["featured_image_url"] == "https://cdn.example/c.jpg"

        # Scenario: Removing the cover clears featured_image_url
        response = await _put(admin_client, updated, {"content": v2_content("Body")})
        assert response.status_code == 200
        assert response.json()["featured_image_url"] is None
        assert response.json()["content"]["cover"] is None

    async def test_client_featured_image_url_alone_is_ignored(
        self, admin_client: AsyncClient
    ) -> None:
        post = await _create(admin_client, content=v2_content("Body"))
        response = await _put(
            admin_client, post, {"featured_image_url": "https://cdn.example/y.jpg"}
        )
        assert response.status_code == 200
        assert response.json()["featured_image_url"] is None


class TestPublishGuard:
    # Scenario: A null cover does not block publish and cards use a fallback
    async def test_null_cover_post_publishes(self, admin_client: AsyncClient) -> None:
        post = await _create(admin_client, content=v2_content("Corpo"))
        await _set_fields(post["id"], status=BlogPostStatus.APPROVED.value)
        response = await admin_client.post(f"{BLOG_POSTS_URL}/{post['id']}/publish")
        assert response.status_code == 200, response.text
        assert response.json()["status"] == BlogPostStatus.PUBLISHED.value
        assert response.json()["featured_image_url"] is None

    async def test_empty_document_is_not_publishable(
        self, admin_client: AsyncClient
    ) -> None:
        post = await _create(admin_client)
        await _set_fields(post["id"], status=BlogPostStatus.APPROVED.value)
        response = await admin_client.post(f"{BLOG_POSTS_URL}/{post['id']}/publish")
        assert response.status_code == 422
        assert response.json()["detail"] == ERR_BLOG_NOT_PUBLISHABLE

    async def test_legacy_row_is_not_publishable(
        self, admin_client: AsyncClient
    ) -> None:
        post = await _create(admin_client, content=v2_content("Corpo"))
        await _set_fields(
            post["id"],
            status=BlogPostStatus.APPROVED.value,
            content={"markdown": "## A\n\nb"},
        )
        response = await admin_client.post(f"{BLOG_POSTS_URL}/{post['id']}/publish")
        assert response.status_code == 422
        assert response.json()["detail"].startswith(ERR_BLOG_NOT_PUBLISHABLE)


class TestPublicProjection:
    async def _published(self, client: AsyncClient, content: dict) -> str:
        post = await _create(client, content=v2_content("Corpo"))
        await _set_fields(
            post["id"],
            content=content,
            status=BlogPostStatus.PUBLISHED.value,
            published_at=datetime.now(UTC),
        )
        return str(post["id"])

    # Scenario: A published v2 post serializes its own section images
    # Scenario: The public payload is a projection without internal fields
    async def test_public_payload_is_a_projection(
        self, admin_client: AsyncClient
    ) -> None:
        en = {
            "schema": "blog.v2",
            "cover": None,
            "sections": [v2_section("Body EN", "What happened")],
            "quality": QUALITY,
        }
        content = {
            **v2_content("Corpo", "O que aconteceu"),
            "cover": _image("https://cdn.example/cover.jpg", "Capa"),
            "sections": [
                {**v2_section("Corpo", "Um"), "image": _image()},
                v2_section("Dois", "Dois", SEC_2),
            ],
            "quality": QUALITY,
            "translations": {"en": en},
        }
        post_id = await self._published(admin_client, content)

        response = await AsyncClient(
            transport=admin_client._transport, base_url="http://test"
        ).get(f"{PUBLIC_URL}/{post_id}")

        assert response.status_code == 200
        payload = response.json()
        text = response.text
        assert "quality" not in text
        assert "prompt" not in text
        assert '"model"' not in text
        assert SLIDE_IMAGES not in text
        body = payload["content"]
        assert body["sections"][0]["image"]["url"] == "https://cdn.example/x.jpg"
        assert body["sections"][0]["image"]["alt"] == "Diagrama"
        assert body["sections"][1]["image"] is None
        assert body["cover"]["alt"] == "Capa"
        assert body["translations"]["en"]["sections"][0]["heading"] == "What happened"

    # Scenario: A non-v2 public row fails closed with the uniform 404
    async def test_legacy_public_row_is_404(self, admin_client: AsyncClient) -> None:
        post_id = await self._published(
            admin_client,
            {"markdown": "# GPT\n\n## A\n\nCorpo", "translations": {"en": "## E\n\nx"}},
        )
        response = await admin_client.get(f"{PUBLIC_URL}/{post_id}")
        assert response.status_code == 404

    # Scenario: A non-v2 editor read fails closed with the document error
    async def test_editor_read_of_a_legacy_row_is_422(
        self, admin_client: AsyncClient
    ) -> None:
        post = await _create(admin_client, content=v2_content("Corpo"))
        await _set_fields(post["id"], content={"markdown": "## A\n\nCorpo"})
        response = await admin_client.get(f"{BLOG_POSTS_URL}/{post['id']}")
        assert response.status_code == 422
        assert response.json()["detail"] == ERR_BLOG_DOCUMENT_NOT_V2


class TestRestoreVersion:
    async def test_restoring_a_legacy_snapshot_is_422(
        self, admin_client: AsyncClient
    ) -> None:
        post = await _create(admin_client, content=v2_content("Corpo"))
        await _set_fields(
            post["id"],
            version_history=[{"version_number": 1, "snapshot": {"markdown": "x"}}],
        )
        # AE-0424: restore is a content write, so it carries If-Match.
        response = await admin_client.post(
            f"{BLOG_POSTS_URL}/{post['id']}/restore-version/1",
            headers={HTTP_HEADER_IF_MATCH: str(post["lock_version"])},
        )
        assert response.status_code == 422
