"""Helpers of the blog generation routes (AE-0425, ADR-0025).

Loads the raw material of a carousel (persisted slides + the workflow
checkpoint's research and outline), resolves the persona and the section count
(the carousel slide count), and starts the tracked run.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Protocol
from uuid import UUID

import structlog
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.carousel_access import (
    get_carousel_project_for_user,
)
from rag_backend.api.dependencies.database import get_db
from rag_backend.api.dependencies.roles import EditorUser
from rag_backend.api.routes.carousels.deps import get_carousel_repo
from rag_backend.api.routes.carousels.editorial_workflow_routes_support import (
    build_editorial_workflow_service,
)
from rag_backend.api.schemas.blog_generate import (
    BlogGenerationAccepted,
    BlogGenerationState,
)
from rag_backend.application.services.blog.blog_brief import (
    CarouselMaterial,
    StandaloneMaterial,
    carousel_brief,
    standalone_brief,
)
from rag_backend.application.services.blog.blog_generated_document import (
    ImageTitles,
    missing_image_subjects,
)
from rag_backend.application.services.blog.blog_generation_runner import (
    schedule_blog_generation,
)
from rag_backend.application.services.blog.blog_generation_service import (
    GenerationJob,
)
from rag_backend.application.services.blog.blog_section_plan import (
    SectionCountSource,
    default_section_count,
    resolve_section_count,
)
from rag_backend.bootstrap.blog_generation import (
    build_generation_service,
    resolve_persona,
)
from rag_backend.domain.constants.blog_document import GENERATION_STATUS_IN_PROGRESS
from rag_backend.domain.constants.blog_generation import (
    GEN_KEY_WARNINGS,
    GENERATION_MODE_IMAGES_ONLY,
    REQUEST_KEY_PERSONA_ID,
    REQUEST_KEY_SOURCE_URLS,
    REQUEST_KEY_TOPIC,
    WARNING_CAROUSEL_PRIVATE,
)
from rag_backend.domain.models.blog_document import (
    InvalidBlogDocumentError,
    parse_blog_content,
)
from rag_backend.domain.models.blog_generation import (
    GenerationLease,
    GenerationTrace,
    WriterBrief,
)
from rag_backend.domain.models.blog_generation_state import (
    GenerationStart,
    generation_of,
)
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.domain.protocols.repositories import CarouselRepository

logger = structlog.get_logger(__name__)

_LOG_STATE_UNAVAILABLE = "blog_generation_workflow_state_unavailable"
_ERR_SERVICE_UNAVAILABLE = "blog_generation_unavailable"


@dataclass(frozen=True)
class CarouselLoad:
    """Where to read a carousel from, for whom."""

    request: Request
    db: AsyncSession
    repo: CarouselRepository
    user: EditorUser


@dataclass(frozen=True)
class PreparedRun:
    """A brief ready to run, plus the row facts the draft needs."""

    brief: WriterBrief | None
    title: str
    warnings: tuple[str, ...]
    # A standalone post takes the writer's title; a carousel post keeps its own.
    retitle: bool = False
    # Images-only retry (``brief is None``): the titles and the empty slots.
    titles: ImageTitles | None = None
    image_slots: int = 0


@dataclass(frozen=True)
class EditorSession:
    """The request's DB session and the authenticated editor."""

    db: AsyncSession
    user: EditorUser


def editor_session(
    db: Annotated[AsyncSession, Depends(get_db)], user: EditorUser
) -> EditorSession:
    """FastAPI dependency: the session + editor pair."""
    return EditorSession(db=db, user=user)


def generation_load(
    request: Request,
    session: Annotated[EditorSession, Depends(editor_session)],
    repo: Annotated[CarouselRepository, Depends(get_carousel_repo)],
) -> CarouselLoad:
    """FastAPI dependency: everything a generation route reads from."""
    return CarouselLoad(request=request, db=session.db, repo=repo, user=session.user)


GenerationLoad = Annotated[CarouselLoad, Depends(generation_load)]


class BlogPostRow(Protocol):
    """The blog row fields an images-only retry reads."""

    id: object
    title: str
    content: dict[str, object]
    ai_generation_metadata: object


def generation_warnings(metadata: object) -> list[str]:
    """The warnings recorded on the previous attempt."""
    warnings = generation_of(metadata).get(GEN_KEY_WARNINGS)
    return (
        [w for w in warnings if isinstance(w, str)]
        if isinstance(warnings, list)
        else []
    )


def now_iso() -> str:
    """UTC now, ISO-8601 (generation timestamps)."""
    return datetime.now(UTC).isoformat()


def new_start(
    kind: str, request: dict[str, object], prepared: PreparedRun
) -> GenerationStart:
    """A fresh attempt with a new lease id (N sections + the cover = N+1 slots)."""
    return GenerationStart(
        kind=kind,
        lease_id=str(uuid.uuid4()),
        now=now_iso(),
        request=request,
        warnings=prepared.warnings,
        image_slots=_slots(prepared),
        mode="" if prepared.brief else GENERATION_MODE_IMAGES_ONLY,
    )


def _slots(prepared: PreparedRun) -> int:
    if prepared.brief is None:
        return prepared.image_slots
    return prepared.brief.section_count + 1


def prepare_images_only(post: BlogPostRow) -> PreparedRun:
    """Retry of a post whose article exists: only its empty image slots run;
    the article is never regenerated."""
    document = parse_blog_content(post.content)
    titles = ImageTitles(title=post.title, en_title=post.title)
    return PreparedRun(
        brief=None,
        title=post.title,
        warnings=tuple(generation_warnings(post.ai_generation_metadata)),
        titles=titles,
        image_slots=len(missing_image_subjects(document, post.title)),
    )


def has_article(content: object) -> bool:
    """True when the stored ``blog.v2`` document has a non-empty section.

    Strict parse (no read fail-safe, which AE-0428 removes): a row that does
    not parse has no article to keep, so the retry runs the full writer (which
    replaces it) instead of failing with a 500.
    """
    try:
        document = parse_blog_content(content)
    except InvalidBlogDocumentError:
        return False
    return any(section.body_md.strip() for section in document.sections)


async def _workflow_state(
    request: Request, project_id: str
) -> Mapping[str, object] | None:
    try:
        state = await build_editorial_workflow_service(request).get_workflow_state(
            project_id
        )
    except Exception:
        logger.warning(_LOG_STATE_UNAVAILABLE, project_id=project_id)
        return None
    return dict(state) if state is not None else None


async def prepare_carousel_run(
    load: CarouselLoad, project_id: UUID, persona_id: str | None
) -> PreparedRun:
    """404 for an unknown/foreign project; otherwise the carousel brief."""
    project = await get_carousel_project_for_user(load.db, project_id, load.user)
    persona = await resolve_persona(load.db, (persona_id, project.persona_id))
    slides = await load.repo.get_slides_by_project(project_id)
    title = project.title or project.topic
    material = CarouselMaterial(
        title=title,
        topic=project.topic,
        persona=persona,
        section_count=resolve_section_count(
            SectionCountSource(
                project.slide_count, project.slides_config, project.content_mode
            )
        ),
        slides=tuple(slides),
        state=await _workflow_state(load.request, str(project_id)),
    )
    warnings = () if project.is_public else (WARNING_CAROUSEL_PRIVATE,)
    return PreparedRun(brief=carousel_brief(material), title=title, warnings=warnings)


async def prepare_standalone_run(
    db: AsyncSession, request: Mapping[str, object]
) -> PreparedRun:
    """The standalone brief (N = the content-mode default, no image max)."""
    topic = str(request.get(REQUEST_KEY_TOPIC) or "")
    persona_id = request.get(REQUEST_KEY_PERSONA_ID)
    persona = await resolve_persona(
        db, (persona_id if isinstance(persona_id, str) else None,)
    )
    urls = request.get(REQUEST_KEY_SOURCE_URLS)
    material = StandaloneMaterial(
        topic=topic,
        persona=persona,
        section_count=default_section_count(None),
        source_urls=tuple(str(url) for url in urls) if isinstance(urls, list) else (),
    )
    return PreparedRun(
        brief=standalone_brief(material), title=topic, warnings=(), retitle=True
    )


def start_run(
    prepared: PreparedRun, job: tuple[GenerationLease, GenerationTrace]
) -> None:
    """Build the run's service (503 if the providers are not wired) and schedule it."""
    lease, trace = job
    persona = prepared.brief.persona if prepared.brief else PersonaProfile()
    try:
        service = build_generation_service(persona, trace.user_id)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_ERR_SERVICE_UNAVAILABLE,
        ) from exc
    schedule_blog_generation(
        service,
        GenerationJob(
            lease=lease,
            trace=trace,
            brief=prepared.brief,
            titles=prepared.titles,
            retitle=prepared.retitle,
        ),
    )


def accepted(
    lease: GenerationLease, start: GenerationStart, attempt: int
) -> BlogGenerationAccepted:
    """The 202 body."""
    return BlogGenerationAccepted(
        id=lease.post_id,
        generation=BlogGenerationState(
            status=GENERATION_STATUS_IN_PROGRESS,
            attempt=attempt,
            warnings=list(start.warnings),
        ),
    )


__all__ = [
    "BlogPostRow",
    "CarouselLoad",
    "EditorSession",
    "GenerationLoad",
    "PreparedRun",
    "accepted",
    "editor_session",
    "generation_load",
    "has_article",
    "new_start",
    "now_iso",
    "prepare_carousel_run",
    "prepare_images_only",
    "prepare_standalone_run",
    "start_run",
]
