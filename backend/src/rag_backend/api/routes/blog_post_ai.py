"""Blog post AI assistance API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.resource_access import (
    get_blog_post_for_user,
    lock_blog_post,
)
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas.blog_post_ai import (
    BlogPostAiImproveRequest,
    BlogPostAiImproveResponse,
    BlogPostAiSuggestRequest,
    BlogPostAiSuggestResponse,
)
from rag_backend.application.services.ai_disclosure_service import AiDisclosureService
from rag_backend.application.services.blog_post_ai_service import (
    BlogAiTraceContext,
    BlogPostAIService,
    _ImproveInput,
    _SuggestInput,
)
from rag_backend.application.services.editorial_audit_service import (
    EditorialAuditService,
    _AuditEntry,
)
from rag_backend.application.services.workflow_event_service import WorkflowEventService
from rag_backend.domain.constants.access_control import ERR_INVALID_REQUEST
from rag_backend.domain.constants.ai_disclosure import (
    AI_ACTION_IMPROVE,
    AI_ACTION_SUGGEST,
)
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_AI_ENDPOINTS
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.events.factory import get_event_publisher

router = APIRouter(tags=["blog_post_ai"])


def _audit_service() -> EditorialAuditService:
    return EditorialAuditService(blog_event_service())


def _disclosure_service() -> AiDisclosureService:
    return AiDisclosureService()


async def _record_ai_action(
    db: AsyncSession,
    post: object,
    post_id: UUID,
    user_id: str,
    action: str,
) -> None:
    metadata = dict(getattr(post, "ai_generation_metadata", {}) or {})
    updated = _disclosure_service().record_action(metadata, action)
    post.ai_generation_metadata = updated  # type: ignore[attr-defined]
    post.ai_disclosure_label = updated.get("ai_disclosure_label", "none")  # type: ignore[attr-defined]
    await _audit_service().log_ai_action(
        db,
        entry=_AuditEntry(
            post_id=str(post_id),
            user_id=user_id,
            extra=action,
        ),
    )


async def _authorize_then_release(
    db: AsyncSession, post_id: UUID, user: EditorUser
) -> str:
    """Check access, then end the read transaction before the LLM call.

    the post loaded here must not be written back after the call — a
    budget reservation or AI action committed meanwhile would be erased. The
    write re-reads the row with :func:`lock_blog_post` and merges onto it.
    """
    await get_blog_post_for_user(db, post_id, user)
    user_id = str(user.id)
    await db.rollback()
    return user_id


def blog_event_service() -> WorkflowEventService:
    """The workflow event service of the blog editor routes."""
    settings = get_settings()
    return WorkflowEventService(get_event_publisher(settings.redis_url or None))


def _build_ai_service() -> BlogPostAIService:
    container = get_container()
    return BlogPostAIService(llm_service=container.llm_service())


@router.post(
    "/blog-posts/{post_id}/ai-suggest",
    response_model=BlogPostAiSuggestResponse,
    summary="Generate AI suggestion for blog text",
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def ai_suggest(
    request: Request,
    post_id: UUID,
    body: BlogPostAiSuggestRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> BlogPostAiSuggestResponse:
    """Generate an AI suggestion for selected blog text.

    The post is re-read under the row lock after the call, so the suggestions merge onto
    what was committed meanwhile.
    """
    user_id = await _authorize_then_release(db, post_id, current_user)
    service = _build_ai_service()
    try:
        result = await service.suggest(
            _SuggestInput(
                text=body.text,
                action=body.suggestion_type,
                context=body.context,
                trace=BlogAiTraceContext(post_id=str(post_id), user_id=user_id),
            )
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_INVALID_REQUEST,
        ) from None

    post = await lock_blog_post(db, post_id)
    post.ai_suggestions = [
        *(post.ai_suggestions or []),
        {**result, "applied": False},
    ]
    await _record_ai_action(db, post, post_id, user_id, AI_ACTION_SUGGEST)
    await db.commit()
    return BlogPostAiSuggestResponse(**result)


@router.post(
    "/blog-posts/{post_id}/ai-improve",
    response_model=BlogPostAiImproveResponse,
    summary="Improve blog text with AI",
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def ai_improve(
    request: Request,
    post_id: UUID,
    body: BlogPostAiImproveRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> BlogPostAiImproveResponse:
    """Improve selected blog text, optionally using a persona voice."""
    user_id = await _authorize_then_release(db, post_id, current_user)
    service = _build_ai_service()
    try:
        result = await service.improve(
            _ImproveInput(
                db=db,
                text=body.text,
                action=body.action,
                context=body.context,
                persona_id=body.persona_id,
                trace=BlogAiTraceContext(post_id=str(post_id), user_id=user_id),
            )
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_INVALID_REQUEST,
        ) from None
    post = await lock_blog_post(db, post_id)
    await _record_ai_action(db, post, post_id, user_id, AI_ACTION_IMPROVE)
    await db.commit()
    return BlogPostAiImproveResponse(**result)
