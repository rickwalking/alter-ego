"""Unit tests: the blog reviewer resolution (AE-0441).

Feature: backend/tests/features/blog_post_ai_contract_ae0424.feature
(review section: the author may review their own post).
"""

import inspect
from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

import rag_backend.api.routes.blog_post_workflow as workflow
from rag_backend.api.routes.blog_post_workflow import resolve_blog_reviewer
from rag_backend.domain.constants.blog_post import BlogPostStatus

POST_ID = UUID("550e8400-e29b-41d4-a716-446655440041")
AUTHOR_ID = "author-1"

SubmitHandler = Callable[..., Awaitable[object]]


class TestResolveBlogReviewer:
    # Scenario: Submit review moves a draft to under_review (distinct reviewer)
    def test_keeps_the_requested_reviewer(self) -> None:
        assert resolve_blog_reviewer("rev-1", "author-1", "user-1") == "rev-1"

    # Scenario: The author may name themselves as the reviewer
    def test_accepts_the_author_as_reviewer(self) -> None:
        assert resolve_blog_reviewer("author-1", "author-1", "user-1") == "author-1"

    # Scenario: Submit review without a reviewer assigns the author
    def test_defaults_to_the_author(self) -> None:
        assert resolve_blog_reviewer(None, "author-1", "user-1") == "author-1"

    def test_falls_back_to_the_current_user_without_an_author(self) -> None:
        assert resolve_blog_reviewer(None, None, "user-1") == "user-1"


def _submit_handler() -> SubmitHandler:
    """The route function itself (slowapi wraps it; unwrap for a direct call)."""
    return cast(SubmitHandler, inspect.unwrap(workflow.submit_blog_post_for_review))


@pytest.mark.unit
@pytest.mark.asyncio
class TestSubmitReviewHandler:
    """Handler-level, like ``test_blog_post_images_ae0439`` (no HTTP transport)."""

    # Scenario: Submit review without a reviewer assigns the author
    async def test_the_author_submits_with_no_reviewer(self) -> None:
        post = SimpleNamespace(
            id=POST_ID,
            status=BlogPostStatus.DRAFT.value,
            author_id=AUTHOR_ID,
            title="Post",
        )
        user = SimpleNamespace(id=AUTHOR_ID)
        db = AsyncMock()
        validate = AsyncMock()
        notify = AsyncMock()
        with (
            patch.object(
                workflow, "get_blog_post_for_user", AsyncMock(return_value=post)
            ),
            patch.object(workflow, "lock_blog_post", AsyncMock(return_value=post)),
            patch.object(workflow, "assert_ready_to_publish"),
            patch.object(workflow, "validate_reviewer_user", validate),
            patch.object(workflow, "bump_lock_version"),
            patch.object(workflow, "_emit_status_change", AsyncMock()),
            patch.object(workflow.NotificationService, "create_review_request", notify),
        ):
            result = await _submit_handler()(MagicMock(), POST_ID, db, user, None)
        assert result is post
        assert post.reviewer_id == AUTHOR_ID
        assert post.status == BlogPostStatus.UNDER_REVIEW.value
        validate.assert_awaited_once_with(db, AUTHOR_ID)
        notify.assert_not_awaited()
