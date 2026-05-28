"""Resource ownership checks for API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import ERR_CAROUSEL_NOT_FOUND
from rag_backend.domain.constants.access_control import (
    ERR_ACCESS_DENIED_NOT_OWNER,
    ERR_CONVERSATION_ACCESS_DENIED,
)
from rag_backend.domain.constants.blog_ai import ERR_BLOG_POST_NOT_FOUND
from rag_backend.domain.constants.blog_post import BlogPostStatus
from rag_backend.domain.constants.workflow_events import (
    AGGREGATE_TYPE_BLOG_POST,
    AGGREGATE_TYPE_PROJECT,
)
from rag_backend.domain.constants.workflow_validation import (
    CONTENT_TYPE_BLOG_POST,
    CONTENT_TYPE_CAROUSEL,
    ERR_BLOG_INVALID_STATUS,
    ERR_INVALID_CONTENT_TYPE,
    ERR_NOT_ASSIGNED_REVIEWER,
    ERR_REVIEWER_ASSIGNMENT_UNSUPPORTED,
    ERR_REVIEWER_INVALID,
    ERR_SELF_REVIEW,
    ERR_WORKFLOW_FIELD_IMMUTABLE,
    WORKFLOW_IMMUTABLE_UPDATE_FIELDS,
)
from rag_backend.domain.models import Conversation, Document, User
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.database.models import BlogPostModel, UserModel
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel


def _user_is_admin(user: UserModel) -> bool:
    return user.role == UserRole.ADMIN.value


def assert_owner_or_admin(resource_owner_id: str | None, user: UserModel) -> None:
    """Raise 403 when the user is neither admin nor resource owner."""
    if _user_is_admin(user):
        return
    if resource_owner_id is None or resource_owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERR_ACCESS_DENIED_NOT_OWNER,
        )


def assert_domain_owner_or_admin(
    resource_owner_id: str | UUID | None,
    user: User,
) -> None:
    """Raise 403 when the domain user is neither admin nor resource owner."""
    if user.is_admin():
        return
    owner_str = str(resource_owner_id) if resource_owner_id is not None else None
    if owner_str is None or owner_str != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERR_ACCESS_DENIED_NOT_OWNER,
        )


def assert_conversation_access(conversation: Conversation, user: User) -> None:
    """Ensure the authenticated user owns the conversation."""
    if conversation.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERR_CONVERSATION_ACCESS_DENIED,
        )
    assert_domain_owner_or_admin(conversation.user_id, user)


def assert_document_access(document: Document, user: User) -> None:
    """Ensure the authenticated user owns the document."""
    assert_domain_owner_or_admin(document.owner_id, user)


def guard_blog_post_update_fields(
    update_data: dict[str, object],
    *,
    is_admin: bool,
) -> None:
    """Reject workflow fields on PUT; strip ownership fields for non-admins."""
    if not is_admin:
        update_data.pop("author_id", None)
        update_data.pop("reviewer_id", None)
    for field in WORKFLOW_IMMUTABLE_UPDATE_FIELDS:
        if field in update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERR_WORKFLOW_FIELD_IMMUTABLE,
            )


async def get_blog_post_for_user(
    db: AsyncSession,
    post_id: UUID,
    user: UserModel,
) -> BlogPostModel:
    """Load a blog post and verify the caller may edit it."""
    post = await db.get(BlogPostModel, str(post_id))
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_BLOG_POST_NOT_FOUND.format(post_id=post_id),
        )
    assert_owner_or_admin(post.author_id, user)
    return post


async def get_blog_post_for_read(
    db: AsyncSession,
    post_id: UUID,
    user: UserModel,
) -> BlogPostModel:
    """Load a blog post and verify the caller may read it."""
    post = await db.get(BlogPostModel, str(post_id))
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_BLOG_POST_NOT_FOUND.format(post_id=post_id),
        )
    if _user_is_admin(user):
        return post
    if _user_is_assigned_reviewer(post.reviewer_id, user):
        return post
    assert_owner_or_admin(post.author_id, user)
    return post


async def get_blog_post_by_id(
    db: AsyncSession,
    post_id: UUID,
) -> BlogPostModel:
    """Load a blog post without ownership check."""
    post = await db.get(BlogPostModel, str(post_id))
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_BLOG_POST_NOT_FOUND.format(post_id=post_id),
        )
    return post


def assert_blog_post_status(
    post: BlogPostModel, expected_status: BlogPostStatus
) -> None:
    """Raise when the post is not in the expected workflow status."""
    if post.status != expected_status.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_BLOG_INVALID_STATUS,
        )


def assert_blog_post_reviewer_or_admin(post: BlogPostModel, user: UserModel) -> None:
    """Ensure the caller is the assigned reviewer or an admin."""
    if _user_is_admin(user):
        return
    if post.reviewer_id is None or post.reviewer_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERR_NOT_ASSIGNED_REVIEWER,
        )


async def validate_reviewer_user(db: AsyncSession, reviewer_id: str) -> UserModel:
    """Ensure the reviewer exists and can review content."""
    reviewer = await db.get(UserModel, reviewer_id)
    if reviewer is None or not reviewer.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_REVIEWER_INVALID,
        )
    if reviewer.role not in {UserRole.ADMIN.value, UserRole.EDITOR.value}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_REVIEWER_INVALID,
        )
    return reviewer


def _user_is_assigned_reviewer(reviewer_id: str | None, user: UserModel) -> bool:
    return reviewer_id is not None and reviewer_id == user.id


async def assert_content_owner_or_admin(
    db: AsyncSession,
    content_id: str,
    content_type: str,
    user: UserModel,
) -> None:
    """Verify the user owns the content or is an admin (not assigned reviewers)."""
    if content_type == CONTENT_TYPE_BLOG_POST:
        post = await db.get(BlogPostModel, content_id)
        if post is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERR_BLOG_POST_NOT_FOUND.format(post_id=content_id),
            )
        assert_owner_or_admin(post.author_id, user)
        return
    if content_type == CONTENT_TYPE_CAROUSEL:
        project = await db.get(CarouselProjectModel, content_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERR_CAROUSEL_NOT_FOUND,
            )
        assert_owner_or_admin(project.owner_id, user)
        return
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ERR_INVALID_CONTENT_TYPE,
    )


async def assert_content_access(
    db: AsyncSession,
    content_id: str,
    content_type: str,
    user: UserModel,
) -> None:
    """Verify the user may access workflow content (blog post or carousel)."""
    if content_type == CONTENT_TYPE_BLOG_POST:
        post = await db.get(BlogPostModel, content_id)
        if post is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERR_BLOG_POST_NOT_FOUND.format(post_id=content_id),
            )
        if _user_is_admin(user):
            return
        if _user_is_assigned_reviewer(post.reviewer_id, user):
            return
        assert_owner_or_admin(post.author_id, user)
        return
    if content_type == CONTENT_TYPE_CAROUSEL:
        project = await db.get(CarouselProjectModel, content_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERR_CAROUSEL_NOT_FOUND,
            )
        if _user_is_admin(user):
            return
        if _user_is_assigned_reviewer(project.assigned_reviewer_id, user):
            return
        assert_owner_or_admin(project.owner_id, user)
        return
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ERR_INVALID_CONTENT_TYPE,
    )


async def assert_audit_aggregate_access(
    db: AsyncSession,
    aggregate_type: str,
    aggregate_id: str,
    user: UserModel,
) -> None:
    """Verify the user may read audit logs for an aggregate."""
    if aggregate_type == AGGREGATE_TYPE_BLOG_POST:
        content_type = CONTENT_TYPE_BLOG_POST
    elif aggregate_type == AGGREGATE_TYPE_PROJECT:
        content_type = CONTENT_TYPE_CAROUSEL
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_INVALID_CONTENT_TYPE,
        )
    await assert_content_access(db, aggregate_id, content_type, user)


async def assign_content_reviewer(
    db: AsyncSession,
    content_id: str,
    content_type: str,
    reviewer_id: str,
) -> None:
    """Persist reviewer assignment on supported content types."""
    if content_type != CONTENT_TYPE_BLOG_POST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_REVIEWER_ASSIGNMENT_UNSUPPORTED,
        )
    post = await db.get(BlogPostModel, content_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_BLOG_POST_NOT_FOUND.format(post_id=content_id),
        )
    if post.author_id and post.author_id == reviewer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_SELF_REVIEW,
        )
    post.reviewer_id = reviewer_id
    await db.flush()


__all__ = [
    "assert_audit_aggregate_access",
    "assert_blog_post_reviewer_or_admin",
    "assert_blog_post_status",
    "assert_content_access",
    "assert_content_owner_or_admin",
    "assert_conversation_access",
    "assert_document_access",
    "assert_domain_owner_or_admin",
    "assert_owner_or_admin",
    "assign_content_reviewer",
    "get_blog_post_by_id",
    "get_blog_post_for_read",
    "get_blog_post_for_user",
    "guard_blog_post_update_fields",
    "validate_reviewer_user",
]
