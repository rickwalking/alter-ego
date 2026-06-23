import shutil
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.constants import (
    ERR_CAROUSEL_NOT_FOUND,
    ERR_FORBIDDEN,
    ERR_NOT_AUTHENTICATED,
    ERR_NOT_FOUND,
)
from rag_backend.api.dependencies import (
    get_optional_user,
    require_authenticated_user,
    require_editor_or_admin,
)
from rag_backend.api.dependencies.carousel_access import (
    get_carousel_project_for_domain_user,
)
from rag_backend.api.dependencies.presentation import get_presentation_handlers
from rag_backend.api.dependencies.publishing import (
    PublishingComposition,
    build_publishing_module,
)
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.schemas import (
    CarouselProjectCreate,
    CarouselProjectListResponse,
    CarouselProjectResponse,
)
from rag_backend.domain.constants.carousel_workflow import (
    ERR_CAROUSEL_NOT_COMPLETED,
    ERR_WORKFLOW_NOT_APPROVED_FOR_PUBLISH,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_CAROUSEL_PUBLISH
from rag_backend.domain.models import CarouselProject, CarouselStatus, User
from rag_backend.domain.protocols import CarouselRepository
from rag_backend.domain.protocols.repositories import _ProjectQuery
from rag_backend.infrastructure.database.config import get_session
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.presentation import PresentationHandlers
from rag_backend.modules.publishing import (
    CarouselReleaseCommand,
    PublishingModule,
)

from .deps import get_carousel_repo
from .helpers import assert_carousel_artifacts_healthy

router = APIRouter()


def get_publishing_module_for_carousel(
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PublishingModule:
    """Build the request-scoped publishing facade for the carousel publish edge.

    Binds the facade to the SAME ``get_session`` session + carousel repository the
    publish route already uses, so the release write + the single commit share one
    transaction (ADR-0009 §9). No scheduler is wired (the carousel release path
    never schedules). Resolving the infra collaborators here keeps the shared
    ``api/dependencies/publishing`` edge free of any new ``api -> infrastructure``
    import (the grandfathered baseline only).
    """
    return build_publishing_module(
        PublishingComposition(session=session, carousel_repository=repo),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
    },
)
async def create_carousel(
    request: CarouselProjectCreate,
    user: Annotated[User, Depends(require_editor_or_admin)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CarouselProjectResponse:
    """Create a new carousel project."""
    from rag_backend.domain.models import CarouselTheme

    # Validate the requested theme is a known root key (or "auto") and store it
    # as a plain string reference (AE-0268). Custom-palette references are
    # validated against the catalog from AE-0270.
    theme = CarouselTheme(request.theme).value
    project = CarouselProject(
        topic=request.topic,
        audience=request.audience,
        niche=request.niche,
        slides_config=request.slides_config,
        language=request.language,
        generate_images=request.generate_images,
        image_model=request.image_model,
        image_style=request.image_style,
        theme=theme,
        custom_visual_details=request.custom_visual_details,
    )
    created = await repo.create_project(project)
    model = await session.get(CarouselProjectModel, str(created.id))
    if model is not None:
        model.owner_id = str(user.id)
        await session.commit()
    return CarouselProjectResponse.model_validate(created)


@router.get(
    "",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
    },
)
async def list_carousels(
    user: Annotated[User | None, Depends(get_optional_user)],
    status_filter: Annotated[CarouselStatus | None, Query(alias="status")] = None,
    public_only: Annotated[bool | None, Query(alias="public")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)] = None,
) -> CarouselProjectListResponse:
    """List carousel projects. Anonymous users only see published (is_public) items."""
    force_public = user is None or public_only is True
    owner_id: str | None = None
    if user is not None and not user.is_admin() and not force_public:
        owner_id = str(user.id)
    items = await repo.get_all_projects(
        query=_ProjectQuery(
            status=status_filter,
            public_only=force_public,
            owner_id=owner_id,
            limit=limit,
            offset=offset,
        ),
    )
    total = await repo.count(
        status=status_filter,
        public_only=force_public,
        owner_id=owner_id,
    )
    return CarouselProjectListResponse(
        items=[CarouselProjectResponse.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{project_id}",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_NOT_FOUND},
    },
)
async def get_carousel(
    project_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    session: Annotated[AsyncSession, Depends(get_session)],
    handlers: Annotated[PresentationHandlers, Depends(get_presentation_handlers)],
) -> CarouselProjectResponse:
    """Get a carousel project by ID."""
    await get_carousel_project_for_domain_user(session, project_id, user)
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    if project.output_dir:
        project.design_tokens = handlers.merge_design_tokens(project)
    return CarouselProjectResponse.model_validate(project)


@router.post(
    "/{project_id}/publish",
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_NOT_FOUND},
        409: {"description": "Carousel artifacts incomplete"},
    },
)
@limiter.limit(RATE_LIMIT_CAROUSEL_PUBLISH)
async def publish_carousel(
    request: Request,
    project_id: UUID,
    user: Annotated[User, Depends(require_editor_or_admin)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    session: Annotated[AsyncSession, Depends(get_session)],
    publishing: Annotated[
        PublishingModule, Depends(get_publishing_module_for_carousel)
    ],
) -> CarouselProjectResponse:
    """Mark a carousel as publicly visible on the homepage and blog."""
    await get_carousel_project_for_domain_user(session, project_id, user)
    model = await session.get(CarouselProjectModel, str(project_id))
    if model is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    if model.workflow_status != WORKFLOW_STATUS_APPROVED_FOR_PUBLISH:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERR_WORKFLOW_NOT_APPROVED_FOR_PUBLISH,
        )
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    if project.status != CarouselStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERR_CAROUSEL_NOT_COMPLETED,
        )
    slides = await repo.get_slides_by_project(project_id)
    assert_carousel_artifacts_healthy(project, slides)
    if not project.blog_markdown:
        from rag_backend.application.services.carousel.editorial_distribution_blog import (
            BlogBuildContext,
            build_blog_markdown_en_from_translations,
            build_blog_markdown_from_drafts,
        )
        from rag_backend.application.services.carousel.editorial_distribution_constants import (
            BLOG_LANG_ENGLISH,
            BLOG_LANG_PORTUGUESE,
            LONG_FORM_NOTES_KEY,
            SLIDE_DRAFT_TEXT_KEY,
            SLIDE_INDEX_KEY,
        )
        from rag_backend.application.services.carousel.types import unpack_extras

        draft_payload: list[dict[str, object]] = []
        translations_en: dict[int, dict[str, object]] = {}
        for slide in slides:
            slide_data = unpack_extras(slide)
            draft_entry: dict[str, object] = {
                SLIDE_INDEX_KEY: slide.slide_number,
                "title": slide.heading,
                SLIDE_DRAFT_TEXT_KEY: slide.body,
            }
            if slide_data.long_form_notes:
                draft_entry[LONG_FORM_NOTES_KEY] = slide_data.long_form_notes
            draft_payload.append(draft_entry)
            if slide_data.translation_en:
                translations_en[slide.slide_number] = slide_data.translation_en
        if draft_payload:
            blog_pt = build_blog_markdown_from_drafts(
                BlogBuildContext(
                    slide_drafts=draft_payload,
                    title=project.title or project.topic,
                ),
            )
            blog_en = build_blog_markdown_en_from_translations(
                BlogBuildContext(
                    slide_drafts=draft_payload,
                    translations_en=translations_en,
                    title=project.title_en or project.title or project.topic,
                ),
            )
            project.blog_markdown = blog_pt
            project.blog_translations = {
                BLOG_LANG_PORTUGUESE: blog_pt,
                BLOG_LANG_ENGLISH: blog_en or blog_pt,
            }
            await repo.update_project(project)
    updated = await publishing.service.release_carousel(
        CarouselReleaseCommand(project=project, project_id=str(project_id)),
    )
    return CarouselProjectResponse.model_validate(updated)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": ERR_NOT_AUTHENTICATED},
        403: {"description": ERR_FORBIDDEN},
        404: {"description": ERR_NOT_FOUND},
    },
)
async def delete_carousel(
    project_id: UUID,
    user: Annotated[User, Depends(require_authenticated_user)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    """Delete a carousel project and its output files."""
    await get_carousel_project_for_domain_user(session, project_id, user)
    project = await repo.get_project_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=ERR_CAROUSEL_NOT_FOUND)
    if project.output_dir:
        output_path = Path(project.output_dir)
        if output_path.exists():
            shutil.rmtree(output_path)
    await repo.delete_project(project_id)
