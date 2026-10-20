"""API tests: review, self-review, publish guard and scheduling (AE-0424).

Feature: backend/tests/features/blog_post_ai_contract_ae0424.feature
(review + scheduled publish, publish guard). AE-0441 removed the blog
"a different editor must review" rule: the author may review their own post.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient

from rag_backend.domain.constants.blog_document import ERR_BLOG_NOT_PUBLISHABLE
from rag_backend.domain.constants.blog_editor import ERR_BLOG_SCHEDULE_NOT_SET
from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.domain.constants.optimistic_locking import (
    ERR_VERSION_CONFLICT,
    HTTP_HEADER_IF_MATCH,
)
from rag_backend.domain.constants.workflow_validation import (
    CONTENT_TYPE_BLOG_POST,
    ERR_REVIEWER_INVALID,
    ERR_SCHEDULE_IN_PAST,
)
from tests.blog_v2_support import v2_content
from tests.integration.blog_editor_support_ae0424 import (
    BLOG_POSTS_URL,
    EditorClients,
    create_post,
    editor_clients,
    get_post,
    if_match,
    put,
    set_fields,
)

APPROVED = BlogPostStatus.APPROVED.value


@pytest.fixture
async def clients(tmp_path: Path) -> AsyncIterator[EditorClients]:
    async with editor_clients(tmp_path) as built:
        yield built


async def _submit(client: AsyncClient, post_id: str, reviewer: str | None = None):
    params = {"reviewer_id": reviewer} if reviewer else None
    return await client.post(f"{BLOG_POSTS_URL}/{post_id}/submit-review", params=params)


def _future(days: int = 2) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


class TestReview:
    # Scenario: Submit review moves a draft to under_review
    async def test_submit_to_distinct_reviewer(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content())
        response = await _submit(clients.author, post["id"], clients.reviewer_id)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == BlogPostStatus.UNDER_REVIEW.value

    # Scenario: The author may name themselves as the reviewer
    async def test_author_names_themselves(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content())
        response = await _submit(clients.author, post["id"], clients.author_id)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == BlogPostStatus.UNDER_REVIEW.value
        assert body["reviewer_id"] == clients.author_id

    # Scenario: Submit review without a reviewer assigns the author
    async def test_missing_reviewer_assigns_the_author(
        self, clients: EditorClients
    ) -> None:
        post = await create_post(clients.author, v2_content())
        response = await _submit(clients.author, post["id"])
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == BlogPostStatus.UNDER_REVIEW.value
        assert body["reviewer_id"] == clients.author_id

    # Scenario: The single author submits, approves and publishes their own post
    async def test_single_author_end_to_end(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content())
        submitted = await _submit(clients.author, post["id"])
        assert submitted.status_code == 200, submitted.text
        url = f"{BLOG_POSTS_URL}/{post['id']}"
        approved = await clients.author.post(f"{url}/approve")
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == APPROVED
        published = await clients.author.post(
            f"{url}/publish", headers=if_match(approved.json())
        )
        assert published.status_code == 200, published.text
        assert published.json()["status"] == BlogPostStatus.PUBLISHED.value
        public = await clients.author.get(f"/api/public/blog-posts/{post['id']}")
        assert public.status_code == 200, public.text

    # Scenario: Submit review still rejects an unknown reviewer
    async def test_unknown_reviewer_is_400(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content())
        response = await _submit(clients.author, post["id"], "no-such-user")
        assert response.status_code == 400
        assert response.json()["detail"] == ERR_REVIEWER_INVALID
        assert (await get_post(clients.author, post["id"]))["status"] == "draft"

    # Scenario: Assigning the author as the reviewer from the review panel is allowed
    async def test_assign_review_accepts_the_author(
        self, clients: EditorClients
    ) -> None:
        post = await create_post(clients.author, v2_content())
        response = await clients.author.post(
            "/api/notifications/assign-review",
            json={
                "reviewer_id": clients.author_id,
                "content_id": post["id"],
                "content_type": CONTENT_TYPE_BLOG_POST,
                "title": "Revisar",
            },
        )
        assert response.status_code == 200, response.text
        stored = await get_post(clients.author, post["id"])
        assert stored["reviewer_id"] == clients.author_id

    # Scenario: Approve moves under_review to approved
    async def test_reviewer_approves(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content())
        await _submit(clients.author, post["id"], clients.reviewer_id)
        response = await clients.reviewer.post(f"{BLOG_POSTS_URL}/{post['id']}/approve")
        assert response.status_code == 200, response.text
        assert response.json()["status"] == APPROVED

    # Scenario: Reject returns an under_review post to draft with a reason
    async def test_reviewer_rejects_with_reason(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content())
        await _submit(clients.author, post["id"], clients.reviewer_id)
        response = await clients.reviewer.post(
            f"{BLOG_POSTS_URL}/{post['id']}/reject", params={"reason": "Falta fonte"}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "draft"
        assert "Falta fonte" in body["editor_comments"][-1]["text"]


class TestTransitionsAreVersioned:
    """Status transitions bump lock_version so a stale write cannot land."""

    async def test_submit_and_approve_bump_the_lock(
        self, clients: EditorClients
    ) -> None:
        post = await create_post(clients.author, v2_content())
        submitted = (
            await _submit(clients.author, post["id"], clients.reviewer_id)
        ).json()
        assert submitted["lock_version"] == post["lock_version"] + 1
        approved = await clients.reviewer.post(f"{BLOG_POSTS_URL}/{post['id']}/approve")
        assert approved.json()["lock_version"] == post["lock_version"] + 2

    # Scenario: Editing after approval resets the post to draft (a save that
    # was prepared before the approval cannot silently skip the reset).
    async def test_save_prepared_before_approval_conflicts(
        self, clients: EditorClients
    ) -> None:
        post = await create_post(clients.author, v2_content())
        await _submit(clients.author, post["id"], clients.reviewer_id)
        await clients.reviewer.post(f"{BLOG_POSTS_URL}/{post['id']}/approve")
        stale = await put(clients.author, post, {"content": v2_content("x")})
        assert stale.status_code == 409
        assert (await get_post(clients.author, post["id"]))["status"] == APPROVED

    # AE-0424 review round 2: transitions re-read their row FOR UPDATE, so an
    # approve overlapping a committed slot write sees its reset to draft.
    async def test_transitions_lock_the_row(
        self, clients: EditorClients, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from rag_backend.api.routes import blog_post_schedule, blog_post_workflow

        locked: list[str] = []
        original = blog_post_workflow.lock_blog_post

        async def spy(db, post_id):
            locked.append(str(post_id))
            return await original(db, post_id)

        monkeypatch.setattr(blog_post_workflow, "lock_blog_post", spy)
        monkeypatch.setattr(blog_post_schedule, "lock_blog_post", spy)
        post = await create_post(clients.author, v2_content())
        await _submit(clients.author, post["id"], clients.reviewer_id)
        await clients.reviewer.post(f"{BLOG_POSTS_URL}/{post['id']}/approve")
        await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/schedule",
            json={"scheduled_publish_at": _future()},
        )
        assert locked == [post["id"]] * 3

    async def test_approve_after_a_reset_to_draft_is_refused(
        self, clients: EditorClients
    ) -> None:
        post = await create_post(clients.author, v2_content())
        submitted = (
            await _submit(clients.author, post["id"], clients.reviewer_id)
        ).json()
        # A content write committed first: the post is back to draft.
        await put(clients.author, submitted, {"content": v2_content("Editado")})
        approve = await clients.reviewer.post(f"{BLOG_POSTS_URL}/{post['id']}/approve")
        assert approve.status_code == 400
        assert (await get_post(clients.author, post["id"]))["status"] == "draft"

    async def test_unpublishable_draft_cannot_be_submitted(
        self, clients: EditorClients
    ) -> None:
        post = await create_post(clients.author, v2_content("  "))
        response = await _submit(clients.author, post["id"], clients.reviewer_id)
        assert response.status_code == 422
        assert response.json()["detail"].startswith(ERR_BLOG_NOT_PUBLISHABLE)
        assert (await get_post(clients.author, post["id"]))["status"] == "draft"


class TestPublishGuard:
    # Scenario: Publishing a draft is rejected by the status guard
    async def test_draft_cannot_publish(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content())
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/publish", headers=if_match(post)
        )
        assert response.status_code == 400
        assert (await get_post(clients.author, post["id"]))["status"] == "draft"

    # Scenario: Publishing an approved post with a valid section succeeds
    async def test_approved_publishes(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content())
        await set_fields(post["id"], status=APPROVED)
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/publish", headers=if_match(post)
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == BlogPostStatus.PUBLISHED.value
        assert response.json()["published_at"] is not None

    # Scenario: Publishing an approved empty document is rejected
    async def test_approved_empty_document_is_422(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content("   "))
        await set_fields(post["id"], status=APPROVED)
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/publish", headers=if_match(post)
        )
        assert response.status_code == 422
        assert response.json()["detail"].startswith(ERR_BLOG_NOT_PUBLISHABLE)
        assert (await get_post(clients.author, post["id"]))["status"] == APPROVED

    async def test_stale_if_match_on_publish_is_409(
        self, clients: EditorClients
    ) -> None:
        post = await create_post(clients.author, v2_content())
        await set_fields(post["id"], status=APPROVED)
        stale = {HTTP_HEADER_IF_MATCH: str(post["lock_version"] + 5)}
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/publish", headers=stale
        )
        assert response.status_code == 409
        assert response.json()["detail"] == ERR_VERSION_CONFLICT

    # Scenario: Unpublish returns the post to draft and 404s publicly
    async def test_unpublish_returns_to_draft(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content())
        await set_fields(post["id"], status=BlogPostStatus.PUBLISHED.value)
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/unpublish", headers=if_match(post)
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "draft"
        public = await clients.author.get(f"/api/public/blog-posts/{post['id']}")
        assert public.status_code == 404


class TestSchedule:
    # Scenario: Scheduling requires approved and a future timestamp
    async def test_schedule_approved_future(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content())
        draft = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/schedule",
            json={"scheduled_publish_at": _future()},
        )
        assert draft.status_code == 400
        await set_fields(post["id"], status=APPROVED)
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/schedule",
            json={"scheduled_publish_at": _future()},
            headers=if_match(post),
        )
        assert response.status_code == 200, response.text
        assert response.json()["scheduled_publish_at"] is not None

    # Scenario: Scheduling in the past is rejected
    async def test_past_schedule_is_rejected(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content())
        await set_fields(post["id"], status=APPROVED)
        past = (datetime.now(UTC) - timedelta(hours=1)).replace(tzinfo=None)
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/schedule",
            json={"scheduled_publish_at": past.isoformat()},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == ERR_SCHEDULE_IN_PAST
        stored = await get_post(clients.author, post["id"])
        assert (stored["status"], stored["scheduled_publish_at"]) == (APPROVED, None)

    # Scenario: Cancelling a schedule leaves the post approved
    async def test_cancel_schedule(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content())
        await set_fields(
            post["id"],
            status=APPROVED,
            scheduled_publish_at=datetime.now(UTC) + timedelta(days=1),
        )
        url = f"{BLOG_POSTS_URL}/{post['id']}/schedule"
        response = await clients.author.delete(url, headers=if_match(post))
        assert response.status_code == 200, response.text
        assert response.json()["scheduled_publish_at"] is None
        assert response.json()["status"] == APPROVED
        again = await clients.author.delete(url)
        assert again.status_code == 409
        assert again.json()["detail"] == ERR_BLOG_SCHEDULE_NOT_SET

    async def test_unpublishable_post_cannot_be_scheduled(
        self, clients: EditorClients
    ) -> None:
        post = await create_post(clients.author, v2_content("  "))
        await set_fields(post["id"], status=APPROVED)
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/schedule",
            json={"scheduled_publish_at": _future()},
        )
        assert response.status_code == 422
        assert (await get_post(clients.author, post["id"]))[
            "scheduled_publish_at"
        ] is None

    async def test_cancel_needs_approved(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content())
        response = await clients.author.delete(
            f"{BLOG_POSTS_URL}/{post['id']}/schedule"
        )
        assert response.status_code == 400

    # Scenario: Editing after approval resets the post to draft and clears the schedule
    async def test_edit_after_schedule_resets(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content())
        await set_fields(
            post["id"],
            status=APPROVED,
            scheduled_publish_at=datetime.now(UTC) + timedelta(days=1),
        )
        await put(clients.author, post, {"content": v2_content("Editado")})
        stored = await get_post(clients.author, post["id"])
        assert (stored["status"], stored["scheduled_publish_at"]) == ("draft", None)
