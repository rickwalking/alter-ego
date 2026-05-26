"""Unit tests for resource ownership helpers."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from rag_backend.api.dependencies.resource_access import (
    assert_content_access,
    assert_content_owner_or_admin,
    assert_owner_or_admin,
    assign_content_reviewer,
    get_blog_post_for_read,
    get_blog_post_for_user,
    get_carousel_project_for_user,
    guard_blog_post_update_fields,
)
from rag_backend.domain.constants.workflow_validation import (
    CONTENT_TYPE_BLOG_POST,
    CONTENT_TYPE_CAROUSEL,
    ERR_REVIEWER_ASSIGNMENT_UNSUPPORTED,
    ERR_SELF_REVIEW,
    ERR_WORKFLOW_FIELD_IMMUTABLE,
)
from rag_backend.domain.models.user import UserRole


def _user(role: UserRole, user_id: str = "user-1") -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.role = role.value
    return user


class TestAssertOwnerOrAdmin:
    def test_admin_bypasses_owner_check(self) -> None:
        assert_owner_or_admin("other-user", _user(UserRole.ADMIN))

    def test_owner_is_allowed(self) -> None:
        assert_owner_or_admin("user-1", _user(UserRole.EDITOR))

    def test_non_owner_raises_forbidden(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            assert_owner_or_admin("other-user", _user(UserRole.EDITOR))

        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
class TestGetBlogPostForUser:
    async def test_returns_post_for_owner(self) -> None:
        post_id = uuid4()
        db = AsyncMock()
        post = MagicMock(author_id="user-1")
        db.get = AsyncMock(return_value=post)

        result = await get_blog_post_for_user(db, post_id, _user(UserRole.EDITOR))

        assert result is post

    async def test_raises_not_found_when_missing(self) -> None:
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_blog_post_for_user(db, uuid4(), _user(UserRole.EDITOR))

        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
class TestGetBlogPostForRead:
    async def test_allows_assigned_reviewer(self) -> None:
        post_id = uuid4()
        db = AsyncMock()
        post = MagicMock(author_id="author-1", reviewer_id="reviewer-1")
        db.get = AsyncMock(return_value=post)

        result = await get_blog_post_for_read(
            db, post_id, _user(UserRole.EDITOR, "reviewer-1")
        )

        assert result is post

    async def test_denies_unrelated_editor(self) -> None:
        db = AsyncMock()
        post = MagicMock(author_id="author-1", reviewer_id="reviewer-1")
        db.get = AsyncMock(return_value=post)

        with pytest.raises(HTTPException) as exc_info:
            await get_blog_post_for_read(db, uuid4(), _user(UserRole.EDITOR, "other"))

        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
class TestGetCarouselProjectForUser:
    async def test_returns_project_for_owner(self) -> None:
        project_id = uuid4()
        db = AsyncMock()
        project = MagicMock(owner_id="user-1")
        db.get = AsyncMock(return_value=project)

        result = await get_carousel_project_for_user(
            db, project_id, _user(UserRole.EDITOR)
        )

        assert result is project

    async def test_raises_forbidden_for_non_owner(self) -> None:
        db = AsyncMock()
        db.get = AsyncMock(return_value=MagicMock(owner_id="other-user"))

        with pytest.raises(HTTPException) as exc_info:
            await get_carousel_project_for_user(db, uuid4(), _user(UserRole.EDITOR))

        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
class TestAssertContentAccess:
    async def test_allows_assigned_reviewer(self) -> None:
        db = AsyncMock()
        post = MagicMock(author_id="author-1", reviewer_id="reviewer-1")
        db.get = AsyncMock(return_value=post)

        await assert_content_access(
            db, "post-1", CONTENT_TYPE_BLOG_POST, _user(UserRole.EDITOR, "reviewer-1")
        )

    async def test_denies_unrelated_editor(self) -> None:
        db = AsyncMock()
        post = MagicMock(author_id="author-1", reviewer_id="reviewer-1")
        db.get = AsyncMock(return_value=post)

        with pytest.raises(HTTPException) as exc_info:
            await assert_content_access(
                db, "post-1", CONTENT_TYPE_BLOG_POST, _user(UserRole.EDITOR, "other")
            )

        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
class TestAssertContentOwnerOrAdmin:
    async def test_allows_blog_post_owner(self) -> None:
        db = AsyncMock()
        post = MagicMock(author_id="author-1")
        db.get = AsyncMock(return_value=post)

        await assert_content_owner_or_admin(
            db, "post-1", CONTENT_TYPE_BLOG_POST, _user(UserRole.EDITOR, "author-1")
        )

    async def test_denies_assigned_reviewer(self) -> None:
        db = AsyncMock()
        post = MagicMock(author_id="author-1", reviewer_id="reviewer-1")
        db.get = AsyncMock(return_value=post)

        with pytest.raises(HTTPException) as exc_info:
            await assert_content_owner_or_admin(
                db,
                "post-1",
                CONTENT_TYPE_BLOG_POST,
                _user(UserRole.EDITOR, "reviewer-1"),
            )

        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
class TestAssignContentReviewer:
    async def test_sets_reviewer_on_blog_post(self) -> None:
        db = AsyncMock()
        post = MagicMock(author_id="author-1", reviewer_id=None)
        db.get = AsyncMock(return_value=post)
        db.flush = AsyncMock()

        await assign_content_reviewer(
            db, "post-1", CONTENT_TYPE_BLOG_POST, "reviewer-1"
        )

        assert post.reviewer_id == "reviewer-1"

    async def test_rejects_self_review(self) -> None:
        db = AsyncMock()
        post = MagicMock(author_id="author-1", reviewer_id=None)
        db.get = AsyncMock(return_value=post)

        with pytest.raises(HTTPException) as exc_info:
            await assign_content_reviewer(
                db, "post-1", CONTENT_TYPE_BLOG_POST, "author-1"
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == ERR_SELF_REVIEW

    async def test_rejects_unsupported_content_type(self) -> None:
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await assign_content_reviewer(
                db, "project-1", CONTENT_TYPE_CAROUSEL, "reviewer-1"
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == ERR_REVIEWER_ASSIGNMENT_UNSUPPORTED


class TestGuardBlogPostUpdateFields:
    def test_rejects_workflow_status_for_non_admin(self) -> None:
        update_data: dict[str, object] = {"title": "Updated", "status": "published"}

        with pytest.raises(HTTPException) as exc_info:
            guard_blog_post_update_fields(update_data, is_admin=False)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == ERR_WORKFLOW_FIELD_IMMUTABLE

    def test_rejects_workflow_status_for_admin(self) -> None:
        update_data: dict[str, object] = {"status": "published"}

        with pytest.raises(HTTPException) as exc_info:
            guard_blog_post_update_fields(update_data, is_admin=True)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == ERR_WORKFLOW_FIELD_IMMUTABLE

    def test_allows_non_workflow_fields_for_admin(self) -> None:
        update_data: dict[str, object] = {"title": "Updated"}

        guard_blog_post_update_fields(update_data, is_admin=True)

        assert update_data["title"] == "Updated"
