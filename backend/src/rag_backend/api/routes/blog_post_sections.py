"""Section voice rewrite and EN translation routes (AE-0424).

- ``POST /blog-posts/{id}/sections/{section_id}/rewrite`` — ``PersonaAgent.enforce``
  on one section's ``body_md`` (the other sections stay byte-identical).
- ``POST /blog-posts/{id}/translations/en`` — builds the missing EN document
  from PT ("Generate EN translation"); 409 when it already exists.

Both writes are ``If-Match`` guarded and stored through the versioned path.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.blog_slot_write import (
    LockedBlogPostRow,
    SlotWrite,
    edit_or_404,
    load_document,
    require_current_version,
    store_document,
)
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.resource_access import get_blog_post_for_user
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.routes.blog_post_ai import (
    _build_ai_service,
    blog_event_service,
    build_blog_translation_service,
)
from rag_backend.api.schemas.blog_post import BlogPostResponse
from rag_backend.api.schemas.blog_post_editor import (
    BlogSectionRewriteRequest,
)
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
    BLOG_EDITOR_LANGUAGE_PATTERN,
    BLOG_LANGUAGE_EN,
    BLOG_LANGUAGE_PT,
    ERR_BLOG_TRANSLATION_EXISTS,
)
from rag_backend.domain.constants.optimistic_locking import HTTP_HEADER_IF_MATCH
from rag_backend.domain.constants.rate_limits import (
    RATE_LIMIT_AI_ENDPOINTS,
)
from rag_backend.domain.models.blog_document import BlogDocument

router = APIRouter(tags=["blog_post_sections"])

Language = Annotated[str, Query(pattern=BLOG_EDITOR_LANGUAGE_PATTERN)]
IfMatch = Annotated[int | None, Header(alias=HTTP_HEADER_IF_MATCH)]


async def _commit_document(db: AsyncSession, write: SlotWrite) -> LockedBlogPostRow:
    await store_document(db, write)
    await db.commit()
    await db.refresh(write.post)
    return write.post


def _addressed(
    post: LockedBlogPostRow, section_id: str, language: str
) -> tuple[BlogDocument, str, str | None]:
    """(document, section body, heading) of the addressed section."""
    document = load_document(post)
    section = edit_or_404(
        lambda: find_section(language_document(document, language), section_id)
    )
    return document, section.body_md, section.heading


@router.post(
    "/blog-posts/{post_id}/sections/{section_id}/rewrite",
    response_model=BlogPostResponse,
    summary="Rewrite one section in the persona voice",
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def rewrite_section(
    request: Request,
    post_id: UUID,
    section_id: str,
    body: BlogSectionRewriteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    if_match: IfMatch = None,
    language: Language = BLOG_LANGUAGE_PT,
) -> LockedBlogPostRow:
    """Replace only that section's ``body_md`` (422 when no persona exists)."""
    post = await get_blog_post_for_user(db, post_id, current_user)
    require_current_version(post, if_match)
    document, body_md, heading = _addressed(post, section_id, language)
    try:
        text = await _build_ai_service().rewrite_section(
            _RewriteInput(
                db=db,
                body_md=body_md,
                heading=heading,
                persona_id=body.persona_id,
                project_id=post.project_id,
                trace=BlogAiTraceContext(post_id=str(post_id), user_id=current_user.id),
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    current = language_document(document, language)
    section = find_section(current, section_id).model_copy(update={"body_md": text})
    updated = with_section(document, language, section)
    write = SlotWrite(
        post=post,
        if_match=if_match,
        document=updated,
        user_id=current_user.id,
        events=blog_event_service(),
        ai_action=AI_ACTION_IMPROVE,
    )
    return await _commit_document(db, write)


@router.post(
    "/blog-posts/{post_id}/translations/en",
    response_model=BlogPostResponse,
    summary="Generate the EN translation of a blog post",
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def generate_en_translation(
    request: Request,
    post_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: EditorUser,
    if_match: IfMatch = None,
) -> LockedBlogPostRow:
    """Translate the PT document into ``translations.en`` (502 on failure)."""
    post = await get_blog_post_for_user(db, post_id, current_user)
    require_current_version(post, if_match)
    document = load_document(post)
    if BLOG_LANGUAGE_EN in document.translations:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=ERR_BLOG_TRANSLATION_EXISTS
        )
    try:
        english = await build_blog_translation_service().translate(
            str(post_id), document
        )
    except BlogTranslationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.code
        ) from exc
    write = SlotWrite(
        post=post,
        if_match=if_match,
        document=with_translation(document, english),
        user_id=current_user.id,
        events=blog_event_service(),
        ai_action=AI_ACTION_IMPROVE,
    )
    return await _commit_document(db, write)
