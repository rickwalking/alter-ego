"""API routes for blog post editorial comments."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.resource_access import get_blog_post_for_user
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.schemas.blog_post import (
    EditorialCommentCreate,
    EditorialCommentListResponse,
    EditorialCommentResponse,
)
from rag_backend.application.services.editorial_audit_service import (
    EditorialAuditService,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.blog_post import EditorialCommentStatus
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.models.source_comment import (
    EditorialCommentModel,
)
from rag_backend.infrastructure.events.factory import get_event_publisher

router = APIRouter(tags=["blog_post_comments"])


def _audit_service() -> EditorialAuditService:
    settings = get_settings()
    return EditorialAuditService(
        WorkflowEventService(get_event_publisher(settings.redis_url or None))
    )


@router.post(
    "/blog-posts/{post_id}/comments",
    response_model=EditorialCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add editorial comment",
)
async def add_blog_post_comment(
    post_id: UUID,
    data: EditorialCommentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> EditorialCommentResponse:
    """Add an editorial comment to a blog post."""
    post = await get_blog_post_for_user(db, post_id, current_user)

    comment = EditorialCommentModel(
        content_id=str(post_id),
        content_type=data.content_type,
        author_id=current_user.id,
        text=data.text,
        position=data.position,
        ai_suggestion=data.ai_suggestion,
        status=EditorialCommentStatus.OPEN,
    )

    post.editor_comments = post.editor_comments or []
    post.editor_comments.append(str(comment.id))

    db.add(comment)
    await _audit_service().log_comment_added(
        db, str(post_id), current_user.id, str(comment.id)
    )
    await db.commit()
    await db.refresh(comment)
    return comment


@router.get(
    "/blog-posts/{post_id}/comments",
    response_model=EditorialCommentListResponse,
    summary="Get editorial comments",
)
async def get_blog_post_comments(
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> EditorialCommentListResponse:
    """Get all editorial comments for a blog post."""
    await get_blog_post_for_user(db, post_id, current_user)
    query = select(EditorialCommentModel).where(
        EditorialCommentModel.content_id == str(post_id),
    )
    result = await db.execute(query)
    comments = result.scalars().all()
    return EditorialCommentListResponse(items=list(comments), total=len(comments))
