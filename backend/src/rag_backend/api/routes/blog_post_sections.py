"""Section voice rewrite and EN translation routes (AE-0424).

- ``POST /blog-posts/{id}/sections/{section_id}/rewrite`` — ``PersonaAgent.enforce``
  on one section's ``body_md`` (the other sections stay byte-identical).
- ``POST /blog-posts/{id}/translations/en`` — builds the missing EN document
  from PT ("Generate EN translation"); 409 when it already exists.

Both writes are ``If-Match`` guarded and stored through the versioned path.
"""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from rag_backend.api.dependencies.blog_editor import (
    IfMatch,
    Language,
    PostTarget,
    Session,
    build_blog_translation_service,
)
from rag_backend.api.dependencies.blog_slot_write import (
    DocumentEdit,
    LockedBlogPostRow,
    SlotEdit,
    apply_slot_edit,
    edit_or_404,
    load_document,
    require_current_version,
)
from rag_backend.api.dependencies.resource_access import get_blog_post_for_user
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.routes.blog_post_ai import _build_ai_service, blog_event_service
from rag_backend.api.routes.carousels.deps import get_carousel_repo
from rag_backend.api.schemas.blog_post import BlogPostResponse
from rag_backend.api.schemas.blog_post_editor import BlogSectionRewriteRequest
from rag_backend.application.services.blog.blog_document_edits import (
    find_section,
    language_document,
    with_section,
    with_translation,
)
from rag_backend.application.services.blog.blog_translation_service import (
    BlogTranslationError,
)
from rag_backend.application.services.blog_post_ai_service import (
    BlogAiTraceContext,
    _RewriteInput,
)
from rag_backend.domain.constants.ai_disclosure import AI_ACTION_IMPROVE
from rag_backend.domain.constants.blog_editor import (
    BLOG_LANGUAGE_EN,
    BLOG_LANGUAGE_PT,
    ERR_BLOG_TRANSLATION_EXISTS,
)
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_AI_ENDPOINTS
from rag_backend.domain.models.blog_document import BlogDocument, BlogLanguageDocument
from rag_backend.domain.protocols import CarouselRepository

router = APIRouter(tags=["blog_post_sections"])


@dataclass
class RewriteTarget:
    """A section rewrite; the carousel repo resolves the project's persona."""

    post_id: UUID
    section_id: str
    db: Session
    current_user: EditorUser
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)]
    if_match: IfMatch = None
    language: Language = BLOG_LANGUAGE_PT


# Path params are fields of the target dataclasses (``Depends()``).
REWRITE_PATH = "/blog-posts/{post_id}/sections/{section_id}/rewrite"
TRANSLATION_PATH = "/blog-posts/{post_id}/translations/en"
Rewrite = Annotated[RewriteTarget, Depends()]
Post = Annotated[PostTarget, Depends()]


def _addressed(
    post: LockedBlogPostRow, section_id: str, language: str
) -> tuple[BlogDocument, str, str | None]:
    """(document, section body, heading) of the addressed section."""
    document = load_document(post)
    section = edit_or_404(
        lambda: find_section(language_document(document, language), section_id)
    )
    return document, section.body_md, section.heading


async def _persona_id(
    target: RewriteTarget, project_id: object, requested: str | None
) -> str | None:
    """The requested persona, else the post's carousel persona (if any)."""
    if requested or not project_id:
        return requested
    project = await target.repo.get_project_by_id(UUID(str(project_id)))
    persona_id = getattr(project, "persona_id", None)
    return str(persona_id) if persona_id else None


async def _rewritten_body(request: _RewriteInput) -> str:
    try:
        return await _build_ai_service().rewrite_section(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


def _with_body(
    document: BlogDocument, target: RewriteTarget, text: str
) -> BlogDocument:
    """The latest document with the rewritten body in that section (by id)."""
    current = language_document(document, target.language)
    section = find_section(current, target.section_id)
    updated = section.model_copy(update={"body_md": text})
    return with_section(document, target.language, updated)


def _with_english(
    document: BlogDocument, english: BlogLanguageDocument
) -> BlogDocument:
    """Store EN unless another request stored one during the spend (409)."""
    if BLOG_LANGUAGE_EN in document.translations:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=ERR_BLOG_TRANSLATION_EXISTS
        )
    return with_translation(document, english)


def _change(target: RewriteTarget | PostTarget, edit: DocumentEdit) -> SlotEdit:
    return SlotEdit(
        post_id=str(target.post_id),
        user_id=str(target.current_user.id),
        edit=edit,
        events=blog_event_service(),
        ai_action=AI_ACTION_IMPROVE,
    )


@router.post(
    REWRITE_PATH,
    response_model=BlogPostResponse,
    summary="Rewrite one section in the persona voice",
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def rewrite_section(
    request: Request,
    body: BlogSectionRewriteRequest,
    target: Rewrite,
) -> LockedBlogPostRow:
    """Replace only that section's ``body_md`` (422 when no persona exists)."""
    post = await get_blog_post_for_user(target.db, target.post_id, target.current_user)
    require_current_version(post, target.if_match)
    _, body_md, heading = _addressed(post, target.section_id, target.language)
    rewrite = _RewriteInput(
        db=target.db,
        body_md=body_md,
        heading=heading,
        persona_id=await _persona_id(target, post.project_id, body.persona_id),
        trace=BlogAiTraceContext(
            post_id=str(target.post_id), user_id=target.current_user.id
        ),
    )
    text = await _rewritten_body(rewrite)
    change = _change(target, lambda latest: _with_body(latest, target, text))
    return await apply_slot_edit(target.db, change)


@router.post(
    TRANSLATION_PATH,
    response_model=BlogPostResponse,
    summary="Generate the EN translation of a blog post",
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def generate_en_translation(request: Request, target: Post) -> LockedBlogPostRow:
    """Translate the PT document into ``translations.en`` (502 on failure)."""
    post = await get_blog_post_for_user(target.db, target.post_id, target.current_user)
    require_current_version(post, target.if_match)
    document = load_document(post)
    if BLOG_LANGUAGE_EN in document.translations:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=ERR_BLOG_TRANSLATION_EXISTS
        )
    user_id = str(target.current_user.id)
    await target.db.rollback()  # no transaction held during the LLM spend
    try:
        english = await build_blog_translation_service().translate(
            str(target.post_id), document
        )
    except BlogTranslationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.code
        ) from exc
    change = SlotEdit(
        post_id=str(target.post_id),
        user_id=user_id,
        edit=lambda latest: _with_english(latest, english),
        events=blog_event_service(),
        ai_action=AI_ACTION_IMPROVE,
    )
    return await apply_slot_edit(target.db, change)
