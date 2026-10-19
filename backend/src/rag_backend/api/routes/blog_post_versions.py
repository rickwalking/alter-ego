"""API routes for blog post version history."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.blog_content_write import (
    ContentWrite,
    require_if_match,
    write_post_content,
)
from rag_backend.api.dependencies.blog_document import validated_write
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.resource_access import get_blog_post_for_user
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.schemas.blog_post import (
    BlogPostResponse,
    BlogPostVersionResponse,
)
from rag_backend.application.services.editorial_audit_service import (
    EditorialAuditService,
    _AuditEntry,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.access_control import ERR_BLOG_VERSION_NOT_FOUND
from rag_backend.domain.constants.blog_editor import VERSION_SUMMARY_RESTORE
from rag_backend.domain.constants.optimistic_locking import HTTP_HEADER_IF_MATCH
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.events.factory import get_event_publisher

router = APIRouter(tags=["blog_post_versions"])


def _event_service() -> WorkflowEventService:
    settings = get_settings()
    return WorkflowEventService(get_event_publisher(settings.redis_url or None))


def _audit_service() -> EditorialAuditService:
    return EditorialAuditService(_event_service())


@router.get(
    "/blog-posts/{post_id}/versions",
    response_model=list[BlogPostVersionResponse],
    summary="Get blog post versions",
)
async def get_blog_post_versions(
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> list[BlogPostVersionResponse]:
    """Get version history of a blog post."""
    post = await get_blog_post_for_user(db, post_id, current_user)
    return post.version_history if post.version_history else []


@router.post(
    "/blog-posts/{post_id}/restore-version/{version_number}",
    response_model=BlogPostResponse,
    summary="Restore blog post to version",
)
async def restore_blog_post_version(
    post_id: UUID,
    version_number: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    if_match: Annotated[int | None, Header(alias=HTTP_HEADER_IF_MATCH)] = None,
) -> BlogPostResponse:
    """Restore a blog post to a previous version (If-Match, snapshotted)."""
    post = await get_blog_post_for_user(db, post_id, current_user)
    require_if_match(if_match)

    versions = post.version_history if post.version_history else []
    version_data: dict | None = None
    for v_data in versions:
        if isinstance(v_data, dict) and v_data.get("version_number") == version_number:
            version_data = v_data
            break

    if not version_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_BLOG_VERSION_NOT_FOUND.format(version_number=version_number),
        )

    # A restore is a content write: strict blog.v2, cover projection synced,
    # If-Match guarded and snapshotted like a save (AE-0424).
    restored = validated_write(
        version_data.get("snapshot", {}), post.ai_generation_metadata
    )
    values: dict[str, object] = {
        "content": restored.content,
        "featured_image_url": restored.featured_image_url,
        "title": version_data.get("title") or post.title,
        "excerpt": version_data.get("excerpt", post.excerpt),
    }
    await write_post_content(
        db,
        ContentWrite(
            post=post,
            if_match=if_match,
            values=values,
            user_id=current_user.id,
            events=_event_service(),
            change_summary=VERSION_SUMMARY_RESTORE.format(
                version_number=version_number
            ),
        ),
    )

    await _audit_service().log_version_restored(
        db,
        entry=_AuditEntry(
            post_id=str(post_id),
            user_id=current_user.id,
            extra=version_number,
        ),
    )
    await db.commit()
    await db.refresh(post)
    return post
