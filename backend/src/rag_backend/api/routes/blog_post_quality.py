"""Blog post quality and analytics API routes (Phase 4)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.feature_flags import RequireQualityChecks
from rag_backend.api.dependencies.resource_access import (
    get_blog_post_for_read,
)
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas.content_quality import (
    AccessibilityCheckResponse,
    AiDisclosureResponse,
    EditorialAnalyticsResponse,
    EditorialAnalyticsSummary,
    EditorialVelocityWeek,
    PlagiarismCheckResponse,
    SeoAnalysisResponse,
)
from rag_backend.application.services.accessibility_check_service import AccessibilityCheckService
from rag_backend.application.services.ai_disclosure_service import AiDisclosureService
from rag_backend.application.services.editorial_analytics_service import EditorialAnalyticsService
from rag_backend.application.services.plagiarism_detection_service import PlagiarismDetectionService
from rag_backend.application.services.seo_analysis_service import SeoAnalysisService
from rag_backend.domain.constants.rate_limits import (
    RATE_LIMIT_AI_ENDPOINTS,
    RATE_LIMIT_WORKFLOW_ENDPOINTS,
)
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.external.openai_embeddings import OpenAIEmbeddingService
from rag_backend.infrastructure.telemetry.opentelemetry import start_span

router = APIRouter(tags=["blog_post_quality"], dependencies=[RequireQualityChecks])


def _plagiarism_service() -> PlagiarismDetectionService:
    container = get_container()
    settings = container.settings()
    if settings.openai_api_key.get_secret_value():
        return PlagiarismDetectionService(
            embedding_service=OpenAIEmbeddingService(settings=settings)
        )
    return PlagiarismDetectionService()


def _extract_body_text(content: dict[str, object]) -> str:
    body = content.get("body", "")
    return str(body) if body else ""


@router.post(
    "/blog-posts/{post_id}/plagiarism-check",
    response_model=PlagiarismCheckResponse,
    summary="Check blog post for plagiarism",
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def check_plagiarism(
    request: Request,
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> PlagiarismCheckResponse:
    """Run plagiarism detection against post content and sources."""
    with start_span("quality.plagiarism_check", {"post_id": str(post_id)}):
        post = await get_blog_post_for_read(db, post_id, current_user)
        content_text = _extract_body_text(post.content if isinstance(post.content, dict) else {})
        sources = list(post.sources or [])
        result = await _plagiarism_service().check(content_text, sources)
        return PlagiarismCheckResponse(**result)  # type: ignore[arg-type]


@router.get(
    "/blog-posts/{post_id}/seo-analyze",
    response_model=SeoAnalysisResponse,
    summary="Analyze blog post SEO",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def analyze_seo(
    request: Request,
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> SeoAnalysisResponse:
    """Analyze SEO readiness of a blog post."""
    with start_span("quality.seo_analyze", {"post_id": str(post_id)}):
        post = await get_blog_post_for_read(db, post_id, current_user)
        service = SeoAnalysisService()
        result = service.analyze(
            title=post.title,
            slug=post.slug,
            meta_title=post.meta_title,
            meta_description=post.meta_description,
            excerpt=post.excerpt,
            keywords=list(post.keywords or []),
        )
        return SeoAnalysisResponse(**result)  # type: ignore[arg-type]


@router.get(
    "/blog-posts/{post_id}/accessibility-check",
    response_model=AccessibilityCheckResponse,
    summary="Check blog post accessibility",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def check_accessibility(
    request: Request,
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> AccessibilityCheckResponse:
    """Check accessibility of blog post content."""
    with start_span("quality.accessibility_check", {"post_id": str(post_id)}):
        post = await get_blog_post_for_read(db, post_id, current_user)
        content = post.content if isinstance(post.content, dict) else {}
        service = AccessibilityCheckService()
        result = service.check(
            content=content,
            featured_image_url=post.featured_image_url,
            design_colors=(
                content.get("design_colors")
                if isinstance(content.get("design_colors"), dict)
                else None
            ),
        )
        return AccessibilityCheckResponse(**result)  # type: ignore[arg-type]


@router.get(
    "/blog-posts/{post_id}/ai-disclosure",
    response_model=AiDisclosureResponse,
    summary="Get AI disclosure label",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def get_ai_disclosure(
    request: Request,
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
) -> AiDisclosureResponse:
    """Return AI disclosure label for a blog post."""
    post = await get_blog_post_for_read(db, post_id, current_user)
    metadata = post.ai_generation_metadata if isinstance(post.ai_generation_metadata, dict) else {}
    service = AiDisclosureService()
    label = service.compute_label(metadata)
    action_count = int(metadata.get("ai_action_count", 0)) if isinstance(metadata, dict) else 0
    return AiDisclosureResponse(
        label=label,
        requires_disclosure=service.requires_disclosure(label),
        ai_action_count=action_count,
    )


@router.get(
    "/editorial-analytics",
    response_model=EditorialAnalyticsResponse,
    summary="Get editorial analytics dashboard data",
)
@limiter.limit(RATE_LIMIT_WORKFLOW_ENDPOINTS)
async def get_editorial_analytics(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    weeks: int = Query(8, ge=1, le=52),
) -> EditorialAnalyticsResponse:
    """Return content velocity and quality metrics for dashboard."""
    service = EditorialAnalyticsService()
    author_filter = None if current_user.role == UserRole.ADMIN.value else current_user.id
    summary = await service.get_summary(db, author_id=author_filter)
    velocity = await service.get_velocity_by_week(db, weeks=weeks, author_id=author_filter)
    return EditorialAnalyticsResponse(
        summary=EditorialAnalyticsSummary(**summary),  # type: ignore[arg-type]
        velocity_by_week=[EditorialVelocityWeek(**v) for v in velocity],  # type: ignore[arg-type]
    )
