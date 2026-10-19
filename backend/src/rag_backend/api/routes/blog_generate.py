"""Blog generation entry points (AE-0425, ADR-0025).

* ``POST /blog-posts/from-carousel`` — one continuous article in the owner's
  voice from a carousel's research/outline/notes; 404 for an unknown project,
  409 (with the existing post id) when the project has ANY blog row.
* ``POST /blog-posts/generate`` — a standalone draft from a topic.
* ``POST /blog-posts/{id}/generation/retry`` — the owner's retry of a failed
  run on the SAME row (new lease/attempt; no duplicate row).

All three answer 202, persist a **draft** (never published) and run the
pipeline as a tracked in-process task; the editor polls ``GET
/blog-posts/{id}`` (``ai_generation_metadata.generation``).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.carousel_access import (
    get_carousel_project_for_user,
)
from rag_backend.api.dependencies.resource_access import get_blog_post_for_user
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.api.routes.blog_generate_support import (
    CarouselLoad,
    EditorSession,
    GenerationLoad,
    PreparedRun,
    accepted,
    editor_session,
    has_article,
    new_start,
    prepare_carousel_run,
    prepare_images_only,
    prepare_standalone_run,
    start_run,
)
from rag_backend.api.schemas.blog_generate import (
    BlogFromCarouselRequest,
    BlogGenerateRequest,
    BlogGenerationAccepted,
    BlogGenerationConflict,
)
from rag_backend.bootstrap.blog_generation import (
    GenerationDraftSpec,
    RestartSpec,
    create_generation_draft,
    live_post_id_for_project,
    restart_generation,
    standalone_slug,
)
from rag_backend.domain.constants.blog_document import GENERATION_STATUS_IN_PROGRESS
from rag_backend.domain.constants.blog_generation import (
    BLOG_TITLE_MAX_CHARS,
    CAROUSEL_SLUG_PREFIX,
    ERR_BLOG_POST_EXISTS_FOR_PROJECT,
    ERR_GENERATION_IN_PROGRESS,
    ERR_GENERATION_NOT_RETRYABLE,
    GEN_KEY_ATTEMPT,
    GEN_KEY_KIND,
    GEN_KEY_REQUEST,
    GENERATION_KIND_FROM_CAROUSEL,
    GENERATION_KIND_STANDALONE,
    GENERATION_STATUSES_RETRYABLE,
    REQUEST_KEY_LANGUAGE,
    REQUEST_KEY_PERSONA_ID,
    REQUEST_KEY_PROJECT_ID,
    REQUEST_KEY_SOURCE_URLS,
    REQUEST_KEY_TOPIC,
)
from rag_backend.domain.constants.blog_post import (
    ERR_BLOG_POST_SLUG_CONFLICT,
    BlogPostOrigin,
)
from rag_backend.domain.constants.optimistic_locking import ERR_VERSION_CONFLICT
from rag_backend.domain.constants.rate_limits import RATE_LIMIT_AI_ENDPOINTS
from rag_backend.domain.models.blog_generation import GenerationLease, GenerationTrace
from rag_backend.domain.models.blog_generation_state import (
    generation_of,
    image_spend_of,
    status_of,
)

router = APIRouter(tags=["blog_generate"])

_ACCEPTED = status.HTTP_202_ACCEPTED


def _conflict(post_id: str) -> JSONResponse:
    body = BlogGenerationConflict(
        code=ERR_BLOG_POST_EXISTS_FOR_PROJECT, post_id=post_id
    )
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=body.model_dump())


async def _create_draft(db: AsyncSession, spec: GenerationDraftSpec) -> GenerationLease:
    try:
        lease = await create_generation_draft(db, spec)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=ERR_BLOG_POST_SLUG_CONFLICT
        ) from exc
    await db.commit()
    return lease


@router.post(
    "/blog-posts/from-carousel",
    response_model=BlogGenerationAccepted,
    status_code=_ACCEPTED,
    responses={
        404: {"description": "Unknown project"},
        409: {"model": BlogGenerationConflict},
    },
    summary="Generate a draft blog post from a carousel",
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def create_blog_from_carousel(
    request: Request,
    body: BlogFromCarouselRequest,
    load: GenerationLoad,
) -> BlogGenerationAccepted | JSONResponse:
    """202 + a draft; 404 unknown project; 409 when the project has a blog row."""
    db, current_user = load.db, load.user
    await get_carousel_project_for_user(db, body.project_id, current_user)
    existing = await live_post_id_for_project(db, str(body.project_id))
    if existing is not None:
        return _conflict(existing)
    persona_id = str(body.persona_id) if body.persona_id else None
    prepared = await prepare_carousel_run(load, body.project_id, persona_id)
    start = new_start(
        GENERATION_KIND_FROM_CAROUSEL,
        {
            REQUEST_KEY_PROJECT_ID: str(body.project_id),
            REQUEST_KEY_PERSONA_ID: persona_id,
            REQUEST_KEY_LANGUAGE: body.language,
        },
        prepared,
    )
    lease = await _create_draft(
        db,
        GenerationDraftSpec(
            title=prepared.title[:BLOG_TITLE_MAX_CHARS],
            slug=f"{CAROUSEL_SLUG_PREFIX}{body.project_id}",
            origin=BlogPostOrigin.CAROUSEL.value,
            author_id=current_user.id,
            start=start,
            project_id=str(body.project_id),
        ),
    )
    trace = GenerationTrace(str(body.project_id), current_user.id, lease.post_id)
    start_run(prepared, (lease, trace))
    return accepted(lease, start, attempt=1)


@router.post(
    "/blog-posts/generate",
    response_model=BlogGenerationAccepted,
    status_code=_ACCEPTED,
    summary="Generate a standalone draft blog post from a topic",
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def generate_blog_post(
    request: Request,
    body: BlogGenerateRequest,
    session: Annotated[EditorSession, Depends(editor_session)],
) -> BlogGenerationAccepted:
    """202 + a standalone draft (N = the content-mode default sections)."""
    db, current_user = session.db, session.user
    stored: dict[str, object] = {
        REQUEST_KEY_TOPIC: body.topic.strip(),
        REQUEST_KEY_PERSONA_ID: str(body.persona_id) if body.persona_id else None,
        REQUEST_KEY_LANGUAGE: body.language,
        REQUEST_KEY_SOURCE_URLS: [str(url) for url in body.source_urls],
    }
    prepared = await prepare_standalone_run(db, stored)
    start = new_start(GENERATION_KIND_STANDALONE, stored, prepared)
    lease = await _create_draft(
        db,
        GenerationDraftSpec(
            title=prepared.title[:BLOG_TITLE_MAX_CHARS],
            slug=standalone_slug(prepared.title),
            origin=BlogPostOrigin.STANDALONE.value,
            author_id=current_user.id,
            start=start,
        ),
    )
    trace = GenerationTrace(lease.post_id, current_user.id, lease.post_id)
    start_run(prepared, (lease, trace))
    return accepted(lease, start, attempt=1)


async def _prepare_retry(
    load: CarouselLoad, generation: dict[str, object]
) -> PreparedRun:
    stored = generation.get(GEN_KEY_REQUEST)
    request = dict(stored) if isinstance(stored, dict) else {}
    if generation.get(GEN_KEY_KIND) != GENERATION_KIND_FROM_CAROUSEL:
        return await prepare_standalone_run(load.db, request)
    persona_id = request.get(REQUEST_KEY_PERSONA_ID)
    return await prepare_carousel_run(
        load,
        UUID(str(request.get(REQUEST_KEY_PROJECT_ID))),
        persona_id if isinstance(persona_id, str) else None,
    )


def _assert_retryable(metadata: object) -> None:
    current = status_of(metadata)
    if current == GENERATION_STATUS_IN_PROGRESS:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=ERR_GENERATION_IN_PROGRESS)
    if current not in GENERATION_STATUSES_RETRYABLE:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail=ERR_GENERATION_NOT_RETRYABLE
        )


@router.post(
    "/blog-posts/{post_id}/generation/retry",
    response_model=BlogGenerationAccepted,
    status_code=_ACCEPTED,
    summary="Retry a failed blog generation on the same draft",
)
@limiter.limit(RATE_LIMIT_AI_ENDPOINTS)
async def retry_blog_generation(
    request: Request,
    post_id: UUID,
    load: GenerationLoad,
) -> BlogGenerationAccepted:
    """202: a new lease/attempt on the same row (409 unless the run failed)."""
    db, current_user = load.db, load.user
    post = await get_blog_post_for_user(db, post_id, current_user)
    _assert_retryable(post.ai_generation_metadata)
    generation = generation_of(post.ai_generation_metadata)
    attempt = _attempt_of(generation) + 1
    # An article that exists is never regenerated: only its empty image slots.
    prepared = (
        prepare_images_only(post)
        if has_article(post.content, str(post_id))
        else await _prepare_retry(load, generation)
    )
    prepared = replace(
        prepared, prior_image_spend_usd=image_spend_of(post.ai_generation_metadata)
    )
    stored = generation.get(GEN_KEY_REQUEST)
    start = new_start(
        str(generation.get(GEN_KEY_KIND) or GENERATION_KIND_STANDALONE),
        dict(stored) if isinstance(stored, dict) else {},
        prepared,
    )
    lease = await _restart(db, RestartSpec(str(post_id), int(post.lock_version), start))
    trace_project = str(post.project_id) if post.project_id else lease.post_id
    start_run(
        prepared,
        (lease, GenerationTrace(trace_project, current_user.id, lease.post_id)),
    )
    return accepted(lease, start, attempt=attempt)


async def _restart(db: AsyncSession, spec: RestartSpec) -> GenerationLease:
    lease = await restart_generation(db, spec)
    if lease is None:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail=ERR_VERSION_CONFLICT)
    await db.commit()
    return lease


def _attempt_of(generation: dict[str, object]) -> int:
    attempt = generation.get(GEN_KEY_ATTEMPT)
    return attempt if isinstance(attempt, int) else 0


__all__ = ["router"]
