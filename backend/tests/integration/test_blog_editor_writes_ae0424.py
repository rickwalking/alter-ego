"""API tests: section saves, versions on save and the approval reset (AE-0424).

Feature: backend/tests/features/blog_post_ai_contract_ae0424.feature
Feature: frontend/tests/features/blog_editor_ae0424.feature (backend half)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.domain.constants.optimistic_locking import (
    ERR_VERSION_CONFLICT,
    HTTP_HEADER_IF_MATCH,
)
from tests.blog_v2_support import v2_content, v2_section
from tests.integration.blog_editor_support_ae0424 import (
    BLOG_POSTS_URL,
    SEC_1,
    SEC_2,
    SEC_3,
    EditorClients,
    create_post,
    editor_clients,
    get_post,
    if_match,
    put,
    set_fields,
    three_sections,
    versions,
)


@pytest.fixture
async def clients(tmp_path: Path) -> AsyncIterator[EditorClients]:
    async with editor_clients(tmp_path) as built:
        yield built


def _ids(post: dict) -> list[str]:
    return [section["id"] for section in post["content"]["sections"]]


class TestSectionSaves:
    # Scenario: Editing a section heading and body persists it
    async def test_edit_one_section_keeps_the_others(
        self, clients: EditorClients
    ) -> None:
        post = await create_post(clients.author, three_sections())
        content = post["content"]
        content["sections"][0] = v2_section("Novo corpo", "Novo título", SEC_1)
        response = await put(clients.author, post, {"content": content})
        assert response.status_code == 200, response.text
        stored = await get_post(clients.author, post["id"])
        first, second, _ = stored["content"]["sections"]
        assert (first["heading"], first["body_md"]) == ("Novo título", "Novo corpo")
        assert second == v2_section("Corpo dois", "Dois", SEC_2)

    # Scenario: Adding / deleting / reordering sections (AC2)
    async def test_add_delete_and_reorder(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, three_sections())
        content = post["content"]
        image = {"url": "/api/blog-images/x/a.jpg", "alt": "Arte"}
        content["sections"][2]["image"] = image
        added = v2_section("Nova", None, "sec_9f6f3c1e-8a7b-4c1d-9e2f-0a1b2c3d4e5f")
        content["sections"] = [content["sections"][2], content["sections"][0], added]
        response = await put(clients.author, post, {"content": content})
        assert response.status_code == 200, response.text
        stored = await get_post(clients.author, post["id"])
        assert _ids(stored) == [SEC_3, SEC_1, added["id"]]
        assert stored["content"]["sections"][0]["image"]["url"] == image["url"]

    # Scenario: An empty alt is rejected
    async def test_blank_alt_is_422_and_not_applied(
        self, clients: EditorClients
    ) -> None:
        post = await create_post(clients.author, three_sections())
        content = post["content"]
        content["sections"][0]["image"] = {
            "url": "https://cdn.example/a.jpg",
            "alt": " ",
        }
        response = await put(clients.author, post, {"content": content})
        assert response.status_code == 422
        stored = await get_post(clients.author, post["id"])
        assert stored["lock_version"] == post["lock_version"]

    # Scenario: Saving keeps featured_image_url equal to cover.url
    async def test_cover_projection_on_save(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, three_sections())
        content = post["content"]
        content["cover"] = {"url": "https://cdn/c.jpg", "alt": "Capa"}
        saved = (await put(clients.author, post, {"content": content})).json()
        assert saved["featured_image_url"] == "https://cdn/c.jpg"
        saved["content"]["cover"] = None
        cleared = (
            await put(clients.author, saved, {"content": saved["content"]})
        ).json()
        assert cleared["featured_image_url"] is None


class TestVersionsOnSave:
    # Scenario: Every PUT appends a version snapshot in the save transaction
    async def test_put_appends_one_snapshot(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content("Original"))
        assert await versions(clients.author, post["id"]) == []
        response = await put(
            clients.author, post, {"title": "Novo", "content": v2_content("Editado")}
        )
        assert response.status_code == 200, response.text
        history = await versions(clients.author, post["id"])
        assert len(history) == 1
        assert history[0]["version_number"] == 1
        assert history[0]["title"] == "Novo"
        assert history[0]["snapshot"]["sections"][0]["body_md"] == "Editado"

    # Scenario: Version history accumulates across saves
    async def test_history_accumulates_in_order(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content("v0"))
        first = (await put(clients.author, post, {"content": v2_content("v1")})).json()
        await put(clients.author, first, {"content": v2_content("v2")})
        history = await versions(clients.author, post["id"])
        assert [v["version_number"] for v in history] == [1, 2]
        assert [v["snapshot"]["sections"][0]["body_md"] for v in history] == [
            "v1",
            "v2",
        ]

    # Scenario: Stale If-Match still conflicts (AE-0296 unchanged)
    async def test_stale_if_match_conflicts_without_a_snapshot(
        self, clients: EditorClients
    ) -> None:
        post = await create_post(clients.author, v2_content("v0"))
        await put(clients.author, post, {"content": v2_content("v1")})
        response = await put(clients.author, post, {"content": v2_content("stale")})
        assert response.status_code == 409
        assert response.json()["detail"] == ERR_VERSION_CONFLICT
        assert len(await versions(clients.author, post["id"])) == 1

    async def test_put_without_if_match_is_428(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content("v0"))
        response = await clients.author.put(
            f"{BLOG_POSTS_URL}/{post['id']}", json={"title": "x"}
        )
        assert response.status_code == 428

    # Scenario: A version can be restored
    async def test_restore_matches_the_version_and_is_snapshotted(
        self, clients: EditorClients
    ) -> None:
        post = await create_post(clients.author, v2_content("v0"))
        first = (
            await put(
                clients.author, post, {"title": "T1", "content": v2_content("v1")}
            )
        ).json()
        second = (
            await put(clients.author, first, {"content": v2_content("v2")})
        ).json()
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/restore-version/1", headers=if_match(second)
        )
        assert response.status_code == 200, response.text
        restored = response.json()
        assert restored["content"]["sections"][0]["body_md"] == "v1"
        assert restored["title"] == "T1"
        history = await versions(clients.author, post["id"])
        assert len(history) == 3
        assert history[-1]["change_summary"] == "Restored from version 1"

    async def test_restore_needs_if_match(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content("v0"))
        await put(clients.author, post, {"content": v2_content("v1")})
        url = f"{BLOG_POSTS_URL}/{post['id']}/restore-version/1"
        assert (await clients.author.post(url)).status_code == 428
        stale = {HTTP_HEADER_IF_MATCH: str(post["lock_version"])}
        assert (await clients.author.post(url, headers=stale)).status_code == 409


class TestEditResetsApproval:
    # Scenario: Editing after approval resets the post to draft and clears the schedule
    @pytest.mark.parametrize(
        "status", [BlogPostStatus.APPROVED.value, BlogPostStatus.UNDER_REVIEW.value]
    )
    async def test_content_edit_resets_to_draft(
        self, clients: EditorClients, status: str
    ) -> None:
        post = await create_post(clients.author, v2_content("v0"))
        scheduled = datetime.now(UTC) + timedelta(days=2)
        await set_fields(post["id"], status=status, scheduled_publish_at=scheduled)
        response = await put(clients.author, post, {"content": v2_content("v1")})
        assert response.status_code == 200, response.text
        stored = await get_post(clients.author, post["id"])
        assert stored["status"] == BlogPostStatus.DRAFT.value
        assert stored["scheduled_publish_at"] is None

    async def test_published_edit_stays_published(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content("v0"))
        await set_fields(post["id"], status=BlogPostStatus.PUBLISHED.value)
        await put(clients.author, post, {"content": v2_content("v1")})
        stored = await get_post(clients.author, post["id"])
        assert stored["status"] == BlogPostStatus.PUBLISHED.value

    async def test_due_sweep_skips_an_edited_post(self, clients: EditorClients) -> None:
        from rag_backend.application.services.notification_service import (
            NotificationService,
        )
        from rag_backend.application.services.scheduled_publish_service import (
            ScheduledPublishService,
        )
        from rag_backend.application.services.workflow_event_service import (
            WorkflowEventService,
        )
        from rag_backend.infrastructure.database.config import get_session_maker

        post = await create_post(clients.author, v2_content("v0"))
        past = datetime.now(UTC) - timedelta(minutes=5)
        await set_fields(
            post["id"],
            status=BlogPostStatus.APPROVED.value,
            scheduled_publish_at=past,
        )
        await put(clients.author, post, {"content": v2_content("v1")})
        sweep = ScheduledPublishService(
            get_session_maker(), WorkflowEventService(None), NotificationService()
        )
        assert await sweep.process_due_posts() == 0
        stored = await get_post(clients.author, post["id"])
        assert stored["status"] == BlogPostStatus.DRAFT.value
