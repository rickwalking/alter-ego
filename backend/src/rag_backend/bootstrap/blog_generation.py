"""Composition root of the blog writer + image run (AE-0425, ADR-0025).

Wires the application service to its concrete collaborators: the role-routed
chat models (writer: fast; judgement: reasoning; persona scoring: fast), the
editor's image service (AE-0424: gpt-image-2, one image template, the
blog-images store and its ``GET /api/blog-images/...`` route) and the
lease-fenced SQL store. The API edge imports these builders instead of the
container/infrastructure directly.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.agents.blog_writer import (
    BlogWriterAgent,
    BlogWriterModels,
    PersonaVoiceScorer,
)
from rag_backend.api.dependencies.blog_editor import (
    blog_images_store,
    build_blog_image_service,
    build_blog_translation_service,
)
from rag_backend.application.services.blog.blog_english_gate import (
    EnglishGateDeps,
    EnglishLanguageGate,
)
from rag_backend.application.services.blog.blog_generation_job import (
    BlogGenerationDeps,
    GenerationTimings,
)
from rag_backend.application.services.blog.blog_generation_service import (
    BlogGenerationService,
)
from rag_backend.application.services.blog.blog_image_batch import (
    BlogImageBatchDeps,
    BlogImageBatchService,
)
from rag_backend.application.services.blog.blog_quality_gate import (
    BlogQualityGate,
    QualityGateDeps,
)
from rag_backend.bootstrap.blog_generation_store import (
    RunOwner,
    SlotWriteGenerationStore,
)
from rag_backend.domain.constants.blog_generation import (
    BLOG_DEFAULT_PERSONA_NAME,
    BLOG_GENERATION_HEARTBEAT_SECONDS,
)
from rag_backend.domain.models.persona import PersonaProfile
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.database.blog_generation_drafts import (
    GenerationDraftSpec,
    RestartSpec,
    create_generation_draft,
    live_post_id_for_project,
    restart_generation,
)
from rag_backend.infrastructure.database.blog_generation_store import (
    SqlBlogGenerationReaper,
)
from rag_backend.infrastructure.database.config import get_session_maker
from rag_backend.modules.editorial.public import PovInputsAcl
from rag_backend.modules.publishing.domain.blog_slug import (
    build_blog_slug,
    new_slug_suffix,
)


def standalone_slug(topic: str) -> str:
    """A unique slug for a standalone generated post (topic stem + suffix)."""
    return build_blog_slug(topic, new_slug_suffix())


def _image_batch(settings: Settings) -> BlogImageBatchService:
    """Bulk generation on top of the editor's image service (AE-0424): the same
    gpt-image-2 provider, image template and blog-images store."""
    return BlogImageBatchService(
        BlogImageBatchDeps(
            images=build_blog_image_service(),
            store=blog_images_store(),
            concurrency=settings.blog_image_concurrency,
        )
    )


def _timings(settings: Settings) -> GenerationTimings:
    """The AE-0435 stage budgets: text stage, then per image wave."""
    return GenerationTimings(
        text_timeout_seconds=settings.blog_generation_text_timeout_seconds,
        image_wave_seconds=settings.blog_image_wave_timeout_seconds,
        heartbeat_seconds=BLOG_GENERATION_HEARTBEAT_SECONDS,
    )


def build_generation_service(
    persona: PersonaProfile, user_id: str
) -> BlogGenerationService:
    """The service for one run (voice scorer bound to its persona; content
    writes recorded as ``user_id``'s through AE-0424's slot-write path; the
    EN language repair uses the editor's PT -> EN translation, AE-0435)."""
    container = get_container()
    settings = container.settings()
    roles = container.llm_service().role_models
    writer = BlogWriterAgent(
        BlogWriterModels(fast=roles.fast, reasoning=roles.reasoning)
    )
    gate = BlogQualityGate(
        QualityGateDeps(writer=writer, scorer=PersonaVoiceScorer(persona, roles.fast))
    )
    english = EnglishLanguageGate(
        EnglishGateDeps(translator=build_blog_translation_service(), gate=gate)
    )
    return BlogGenerationService(
        BlogGenerationDeps(
            writer=writer,
            gate=gate,
            english=english,
            images=_image_batch(settings),
            store=SlotWriteGenerationStore(
                get_session_maker(),
                RunOwner(user_id=user_id, image_cap=settings.blog_image_cost_cap),
            ),
            timings=_timings(settings),
        )
    )


def build_blog_generation_reaper(settings: Settings) -> SqlBlogGenerationReaper:
    """The worker-tick reaper of interrupted runs."""
    return SqlBlogGenerationReaper(settings.blog_generation_stale_seconds)


async def resolve_persona(
    db: AsyncSession, candidates: tuple[str | None, ...]
) -> PersonaProfile:
    """The first existing candidate persona, else the owner persona by name.

    Falls back to the default ``PersonaProfile`` when no persona exists, so a
    missing persona never blocks generation (the voice gate still runs).
    """
    acl = PovInputsAcl(db)
    for persona_id in candidates:
        persona = await acl.load_persona(persona_id)
        if persona is not None:
            return persona
    configured = get_settings().autopilot_persona_id.strip()
    named = await acl.resolve_persona_id(configured, BLOG_DEFAULT_PERSONA_NAME)
    persona = await acl.load_persona(named)
    return persona if persona is not None else PersonaProfile()


__all__ = [
    "GenerationDraftSpec",
    "RestartSpec",
    "build_blog_generation_reaper",
    "build_generation_service",
    "create_generation_draft",
    "live_post_id_for_project",
    "resolve_persona",
    "restart_generation",
    "standalone_slug",
]
