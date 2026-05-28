#!/usr/bin/env python3
"""Seed carousel editorial workflow fixtures for Playwright Gherkin E2E.

Feature: frontend/tests/features/carousel_editorial_consolidation.feature

Run inside the backend container:
  uv run python scripts/seed_e2e_carousel_fixtures.py
"""

from __future__ import annotations

import asyncio
import json
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlalchemy import select

from rag_backend.agents.carousel_workflow_engine import CarouselWorkflowEngine
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_FINAL_REVIEW,
    PHASE_IMAGES,
    PHASE_OUTLINE,
    PHASE_RESEARCH,
    PHASE_STATUS_AWAITING_HUMAN,
    PHASE_STATUS_IN_PROGRESS,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.models import CarouselProject, CarouselStatus, CarouselTheme
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.config import (
    close_db,
    get_session_maker,
    init_db,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.infrastructure.database.models.user import UserModel
from rag_backend.infrastructure.database.user_repository import PostgresUserRepository

ADMIN_EMAIL = "admin@alterego.app"

E2E_RESEARCH = "00000000-0000-4000-a000-000000000001"
E2E_OUTLINE = "00000000-0000-4000-a000-000000000002"
E2E_CONTENT_PERSONA = "00000000-0000-4000-a000-000000000003"
E2E_FINAL_REVIEW = "00000000-0000-4000-a000-000000000004"
E2E_APPROVED_PUBLISH = "00000000-0000-4000-a000-000000000005"
E2E_PUBLIC_BLOG = "00000000-0000-4000-a000-000000000006"
E2E_DESIGN_GATE = "00000000-0000-4000-a000-000000000007"
E2E_IMAGES_PROGRESS = "00000000-0000-4000-a000-000000000008"

RESEARCH_FINDINGS: list[dict[str, object]] = [
    {
        "source": "E2E security report",
        "key_points": [
            "Researchers found 3,800 internal repositories exposed",
            "Credentials and API keys were among leaked assets",
        ],
        "summary": "Synthetic research findings for Playwright E2E validation.",
    }
]

OUTLINE_SLIDES: list[dict[str, object]] = [
    {
        "slide_index": 1,
        "title": "Hook slide",
        "key_points": ["Opening hook"],
        "visual_direction": "Bold opener",
    },
    {
        "slide_index": 2,
        "title": "Breach example",
        "key_points": ["Main incident"],
        "visual_direction": "Warning palette",
    },
    {
        "slide_index": 3,
        "title": "Mitigation",
        "key_points": ["Action items"],
        "visual_direction": "Checklist",
    },
]

MINIMAL_DESIGN_TOKENS: dict[str, object] = {
    "colors": {
        "primary": "#0ac5a8",
        "accent": "#8b5cf6",
        "bg": "#080c12",
        "text": "#ffffff",
        "text_muted": "#94a3b8",
        "text_dim": "#64748b",
        "border": "#1e293b",
        "glow": "#8b5cf633",
    },
    "typography": {
        "font_family_body": "Inter, sans-serif",
        "font_family_heading": "Inter, sans-serif",
        "font_family_badge": "Inter, sans-serif",
    },
    "layout": {
        "badge_label": "E2E",
        "swipe_text": "Swipe",
        "progress_segments": 5,
    },
    "images": {
        "hero": "/api/carousels/00000000-0000-4000-a000-000000000006/preview/images/hero.jpg",
        "slides": [],
        "rendered_slides_pt": [],
        "rendered_slides_en": [],
    },
}

BLOG_MARKDOWN = (
    "# E2E Published Blog\n\nThis markdown is seeded for public blog E2E tests.\n"
)


@dataclass(frozen=True)
class FixtureSpec:
    project_id: str
    topic: str
    phase: str
    phase_status: str
    is_public: bool = False
    blog_markdown: str | None = None
    workflow_status: str = ""
    extra_state: dict[str, object] = field(default_factory=dict)
    phase_progress: dict[str, object] | None = None
    design_tokens: dict[str, object] | None = None
    caption: str | None = None


FIXTURES: tuple[FixtureSpec, ...] = (
    FixtureSpec(
        project_id=E2E_RESEARCH,
        topic="E2E Research Gate",
        phase=PHASE_RESEARCH,
        phase_status=PHASE_STATUS_AWAITING_HUMAN,
        extra_state={"research_findings": RESEARCH_FINDINGS},
    ),
    FixtureSpec(
        project_id=E2E_OUTLINE,
        topic="E2E Outline Gate",
        phase=PHASE_OUTLINE,
        phase_status=PHASE_STATUS_AWAITING_HUMAN,
        extra_state={
            "research_findings": RESEARCH_FINDINGS,
            "outline": OUTLINE_SLIDES,
        },
    ),
    FixtureSpec(
        project_id=E2E_CONTENT_PERSONA,
        topic="E2E Content Persona Gate",
        phase=PHASE_CONTENT,
        phase_status=PHASE_STATUS_AWAITING_HUMAN,
        extra_state={
            "research_findings": RESEARCH_FINDINGS,
            "outline": OUTLINE_SLIDES,
            "slide_drafts": [{"slide_index": 1, "draft_text": "Slide body for E2E"}],
            "persona_scores": {"default": {"overall": 65}},
        },
    ),
    FixtureSpec(
        project_id=E2E_FINAL_REVIEW,
        topic="E2E Final Review Gate",
        phase=PHASE_FINAL_REVIEW,
        phase_status=PHASE_STATUS_AWAITING_HUMAN,
        blog_markdown=BLOG_MARKDOWN,
        extra_state={
            "research_findings": RESEARCH_FINDINGS,
            "outline": OUTLINE_SLIDES,
            "caption": "E2E Instagram caption draft",
            "blog_markdown": BLOG_MARKDOWN,
            "rubric_scores": {"voice_match": 88, "clarity": 90},
        },
    ),
    FixtureSpec(
        project_id=E2E_APPROVED_PUBLISH,
        topic="E2E Approved For Publish",
        phase=PHASE_FINAL_REVIEW,
        phase_status=PHASE_STATUS_AWAITING_HUMAN,
        workflow_status=WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
        blog_markdown=BLOG_MARKDOWN,
        caption="E2E caption ready to publish",
        design_tokens=MINIMAL_DESIGN_TOKENS,
        extra_state={
            "research_findings": RESEARCH_FINDINGS,
            "outline": OUTLINE_SLIDES,
            "caption": "E2E caption ready to publish",
            "blog_markdown": BLOG_MARKDOWN,
            "workflow_status": WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
            "quality_passed": True,
        },
    ),
    FixtureSpec(
        project_id=E2E_PUBLIC_BLOG,
        topic="E2E Public Blog",
        phase=PHASE_FINAL_REVIEW,
        phase_status=PHASE_STATUS_AWAITING_HUMAN,
        is_public=True,
        blog_markdown=BLOG_MARKDOWN,
        design_tokens=MINIMAL_DESIGN_TOKENS,
        extra_state={
            "blog_markdown": BLOG_MARKDOWN,
            "workflow_status": WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
        },
    ),
    FixtureSpec(
        project_id=E2E_DESIGN_GATE,
        topic="E2E Design Gate",
        phase=PHASE_DESIGN,
        phase_status=PHASE_STATUS_AWAITING_HUMAN,
        extra_state={
            "research_findings": RESEARCH_FINDINGS,
            "outline": OUTLINE_SLIDES,
            "design_applied": True,
        },
    ),
    FixtureSpec(
        project_id=E2E_IMAGES_PROGRESS,
        topic="E2E Images In Progress",
        phase=PHASE_IMAGES,
        phase_status=PHASE_STATUS_IN_PROGRESS,
        phase_progress={
            "phase": "images",
            "percent": 50,
            "label": "Generating slide 5 of 10",
        },
        extra_state={"image_assets": ["/tmp/e2e/slide_1.jpg"]},
    ),
)


async def _build_checkpointer(stack: AsyncExitStack) -> BaseCheckpointSaver | None:
    settings = get_settings()
    backend = settings.carousel_checkpoint_backend.lower()

    if backend == "disabled":
        return None
    if backend == "memory":
        return InMemorySaver()
    if backend == "postgres":
        if not settings.carousel_checkpoint_postgres_url:
            return InMemorySaver()
        saver_pg = await stack.enter_async_context(
            AsyncPostgresSaver.from_conn_string(
                settings.carousel_checkpoint_postgres_url
            )
        )
        await saver_pg.setup()
        return saver_pg
    if not settings.carousel_checkpoint_sqlite_path:
        return InMemorySaver()
    try:
        Path(settings.carousel_checkpoint_sqlite_path).parent.mkdir(
            parents=True, exist_ok=True
        )
        return await stack.enter_async_context(
            AsyncSqliteSaver.from_conn_string(settings.carousel_checkpoint_sqlite_path)
        )
    except OSError:
        return InMemorySaver()


async def _get_admin_id() -> str:
    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = PostgresUserRepository(session)
        user = await repo.get_by_email(ADMIN_EMAIL)
        if user is None:
            result = await session.execute(
                select(UserModel).where(UserModel.email == ADMIN_EMAIL)
            )
            model = result.scalar_one_or_none()
            if model is None:
                raise RuntimeError(f"Admin user not found: {ADMIN_EMAIL}")
            return str(model.id)
        return str(user.id)


async def _upsert_project(
    owner_id: str,
    spec: FixtureSpec,
) -> None:
    session_maker = get_session_maker()
    async with session_maker() as session:
        model = await session.get(CarouselProjectModel, spec.project_id)
        if model is None:
            entity = CarouselProject(
                id=UUID(spec.project_id),
                topic=spec.topic,
                audience="Developers",
                niche="E2E",
                theme=CarouselTheme.CYBERSECURITY,
                owner_id=owner_id,
                is_public=spec.is_public,
                blog_markdown=spec.blog_markdown,
                caption=spec.caption,
                design_tokens=spec.design_tokens,
                output_dir=f"/app/output/carousels/{spec.project_id}",
                status=CarouselStatus.COMPLETED,
            )
            model = CarouselProjectModel.from_entity(entity)
            model.id = spec.project_id
            session.add(model)
        else:
            model.topic = spec.topic
            model.audience = "Developers"
            model.niche = "E2E"
            model.owner_id = owner_id
            model.is_public = spec.is_public
            model.blog_markdown = spec.blog_markdown
            model.caption = spec.caption
            if spec.design_tokens is not None:
                model.design_tokens = spec.design_tokens
            model.status = CarouselStatus.COMPLETED.value

        model.current_phase = spec.phase
        model.phase_status = spec.phase_status
        model.workflow_status = spec.workflow_status
        model.phase_progress = spec.phase_progress
        model.lock_version = 1
        await session.commit()


async def _seed_checkpoint(engine: CarouselWorkflowEngine, spec: FixtureSpec) -> None:
    brief: dict[str, object] = {
        "topic": spec.topic,
        "audience": "Developers",
        "brief": "E2E fixture",
        "sources": [],
    }
    state_update: dict[str, object] = {
        "current_phase": spec.phase,
        "phase_status": spec.phase_status,
    }
    if spec.workflow_status:
        state_update["workflow_status"] = spec.workflow_status
    state_update.update(spec.extra_state)
    config = engine._run_config(spec.project_id)

    if spec.phase_status == PHASE_STATUS_IN_PROGRESS:
        initial = {
            "project_id": spec.project_id,
            "current_phase": spec.phase,
            "phase_status": spec.phase_status,
            "brief": brief,
            **{
                k: v
                for k, v in state_update.items()
                if k not in {"current_phase", "phase_status"}
            },
        }
        await engine._app.aupdate_state(config, initial, as_node=spec.phase)
        return

    await engine.start(spec.project_id, brief)
    await engine._app.aupdate_state(config, state_update, as_node=spec.phase)


async def seed_all() -> dict[str, str]:
    settings = get_settings()
    await init_db(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )
    admin_id = await _get_admin_id()
    ids: dict[str, str] = {}

    async with AsyncExitStack() as stack:
        checkpointer = await _build_checkpointer(stack)
        engine = CarouselWorkflowEngine(checkpointer=checkpointer)

        for spec in FIXTURES:
            await _upsert_project(admin_id, spec)
            await _seed_checkpoint(engine, spec)
            ids[spec.topic] = spec.project_id
            print(f"  seeded {spec.project_id} -> {spec.phase}/{spec.phase_status}")

    await close_db()
    return ids


def main() -> None:
    print("Seeding E2E carousel editorial fixtures...")
    ids = asyncio.run(seed_all())
    manifest = {
        "research": E2E_RESEARCH,
        "outline": E2E_OUTLINE,
        "contentPersona": E2E_CONTENT_PERSONA,
        "finalReview": E2E_FINAL_REVIEW,
        "approvedPublish": E2E_APPROVED_PUBLISH,
        "publicBlog": E2E_PUBLIC_BLOG,
        "designGate": E2E_DESIGN_GATE,
        "imagesProgress": E2E_IMAGES_PROGRESS,
    }
    print(json.dumps(manifest, indent=2))
    print(f"Done. Seeded {len(ids)} fixtures for {ADMIN_EMAIL}.")


if __name__ == "__main__":
    main()
