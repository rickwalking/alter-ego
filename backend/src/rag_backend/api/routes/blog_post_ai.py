"""Blog post AI assistance API routes."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.blog_document import (
    cover_write,
    validated_write,
)
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.resource_access import get_blog_post_for_user
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas.blog_post_ai import (
    BlogPostAiImproveRequest,
    BlogPostAiImproveResponse,
    BlogPostAiSuggestRequest,
    BlogPostAiSuggestResponse,
    BlogPostGenerateImageRequest,
    BlogPostGenerateImageResponse,
)
from rag_backend.application.services.ai_disclosure_service import AiDisclosureService
from rag_backend.application.services.asset_cdn_service import AssetCdnService
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
from rag_backend.domain.constants import IMAGE_MODEL_OPENAI, IMAGE_STYLE_CINEMATIC
from rag_backend.domain.constants.access_control import ERR_INVALID_REQUEST
from rag_backend.domain.constants.ai_disclosure import (
    AI_ACTION_GENERATE_IMAGE,
    AI_ACTION_IMPROVE,
    AI_ACTION_SUGGEST,
)
from rag_backend.domain.constants.blog_ai import ERR_IMAGE_GENERATION_FAILED
from rag_backend.domain.constants.blog_document import (
    BLOG_IMAGE_SOURCE_GENERATED,
    ERR_BLOG_IMAGE_URL_INVALID,
)
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_AI_ENDPOINTS
from rag_backend.domain.models.blog_document import BlogImage
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.events.factory import get_event_publisher

router = APIRouter(tags=["blog_post_ai"])


def _audit_service() -> EditorialAuditService:
    return EditorialAuditService(blog_event_service())


def _cdn_service() -> AssetCdnService:
    settings = get_settings()
    return AssetCdnService(
        cdn_base_url=settings.cdn_base_url, enabled=settings.cdn_enabled
    )


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


def blog_event_service() -> WorkflowEventService:
    """The workflow event service of the blog editor routes (AE-0424)."""
    settings = get_settings()
    return WorkflowEventService(get_event_publisher(settings.redis_url or None))


def _build_ai_service() -> BlogPostAIService:
    container = get_container()
    settings = container.settings()
    image_registry = container.image_provider_registry()
    image_provider = image_registry.resolve(IMAGE_MODEL_OPENAI, IMAGE_STYLE_CINEMATIC)
    return BlogPostAIService(
        llm_service=container.llm_service(),
        image_service=image_provider.service,
        output_dir=Path(settings.carousel_output_dir) / "blog-images",
    )


@dataclass(frozen=True)
class _CoverText:
    prompt: str
    alt: str


def _cover_image(url: str, text: _CoverText) -> BlogImage:
    """The generated cover; a non-publishable URL is an image failure (502)."""
    try:
        return BlogImage(
            url=url,
            alt=text.alt,
            source=BLOG_IMAGE_SOURCE_GENERATED,
            prompt=text.prompt,
            model=IMAGE_MODEL_OPENAI,
            created_at=datetime.now(UTC).isoformat(),
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ERR_IMAGE_GENERATION_FAILED.format(
                reason=ERR_BLOG_IMAGE_URL_INVALID
            ),
        ) from exc


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
    """Generate an AI suggestion for selected blog text."""
    post = await get_blog_post_for_user(db, post_id, current_user)
    service = _build_ai_service()
    try:
        result = await service.suggest(
            _SuggestInput(
                text=body.text,
                action=body.suggestion_type,
                context=body.context,
                trace=BlogAiTraceContext(post_id=str(post_id), user_id=current_user.id),
            )
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_INVALID_REQUEST,
        ) from None

    suggestions = list(post.ai_suggestions or [])
    suggestions.append({**result, "applied": False})
    post.ai_suggestions = suggestions
    await _record_ai_action(db, post, post_id, current_user.id, AI_ACTION_SUGGEST)
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
    post = await get_blog_post_for_user(db, post_id, current_user)
    service = _build_ai_service()
    try:
        result = await service.improve(
            _ImproveInput(
                db=db,
                text=body.text,
                action=body.action,
                context=body.context,
                persona_id=body.persona_id,
                trace=BlogAiTraceContext(post_id=str(post_id), user_id=current_user.id),
            )
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_INVALID_REQUEST,
        ) from None
    await _record_ai_action(db, post, post_id, current_user.id, AI_ACTION_IMPROVE)
    await db.commit()
    return BlogPostAiImproveResponse(**result)


@router.post(
    "/blog-posts/{post_id}/generate-image",
    response_model=BlogPostGenerateImageResponse,
    summary="Generate featured image for blog post",
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def generate_image(
    request: Request,
    post_id: UUID,
    body: BlogPostGenerateImageRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> BlogPostGenerateImageResponse:
    """Generate the cover image of a blog post (``content.cover`` + projection).

    Fails fast (422) before any image spend when the stored content is not a
    valid ``blog.v2`` document; ``featured_image_url`` is re-projected from the
    new cover in the same transaction (AE-0423).
    """
    post = await get_blog_post_for_user(db, post_id, current_user)
    validated_write(post.content, post.ai_generation_metadata)
    service = _build_ai_service()
    try:
        result = await service.generate_image(
            str(post_id),
            body.prompt,
            user_id=current_user.id,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ERR_IMAGE_GENERATION_FAILED.format(reason="image generation failed"),
        ) from exc

    cover = _cover_image(
        _cdn_service().resolve_url(result["image_url"]),
        _CoverText(prompt=result["prompt"], alt=post.title or result["prompt"]),
    )
    written = cover_write(post.content, cover)
    post.content = written.content
    post.featured_image_url = written.featured_image_url
    metadata = dict(post.ai_generation_metadata or {})
    metadata["last_image_prompt"] = result["prompt"]
    post.ai_generation_metadata = metadata
    await _record_ai_action(
        db, post, post_id, current_user.id, AI_ACTION_GENERATE_IMAGE
    )
    await db.commit()
    return BlogPostGenerateImageResponse(**{
        **result,
        "image_url": post.featured_image_url,
    })
