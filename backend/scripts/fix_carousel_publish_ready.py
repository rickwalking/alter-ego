#!/usr/bin/env python3
"""Sync workflow copy to DB, regenerate on-topic images, and re-render a carousel."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from uuid import UUID

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from rag_backend.agents.carousel_workflow_engine import CarouselWorkflowEngine
from rag_backend.application.services.carousel.editorial_distribution_pack import (
    SlideDraftsContext,
    apply_slide_drafts_to_database,
)
from rag_backend.application.services.carousel.nodes.design import run_design
from rag_backend.application.services.carousel.editorial_visual_pipeline import (
    CarouselImageGenerationContext,
    generate_carousel_images,
)
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.domain.constants import ENCODING_UTF8, LANGUAGE_PT
from rag_backend.application.services.carousel.malformed_draft_normalizer import (
    normalize_slide_drafts,
)
from rag_backend.application.services.carousel.presentation_review import (
    deserialize_translations_en,
    serialize_translations_en,
)
from rag_backend.application.services.carousel.refinement_service import (
    CarouselRefinementConfig,
    CarouselRefinementService,
)
from rag_backend.application.services.carousel.types import unpack_extras
from rag_backend.domain.models.carousel import CarouselStatus
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.config import close_db, get_session, init_db
from rag_backend.infrastructure.logging import setup_logging

PROJECT_TITLE_PT = "Claude Fable 5 e Mythos 5"
def _optimize_generated_images(images_dir: Path) -> None:
    """Shrink hero images so Playwright preflight can decode all slides in time."""
    from PIL import Image

    for image_file in sorted(images_dir.glob("slide_*.jpg")):
        with Image.open(image_file) as img:
            converted = img.convert("RGB")
            converted.thumbnail((1600, 1600))
            converted.save(image_file, "JPEG", quality=82, optimize=True)


def _write_preview_html(
    project,
    slides: list,
    *,
    output_dir: Path,
    strategy_registry: object,
) -> str:
    template = CarouselTemplateBuilder()
    pt_html = run_design(
        project,
        slides,
        template=template,
        strategy_registry=strategy_registry,
        strategy_name=project.slide_layout_strategy or None,
    )
    lang_dir = output_dir / LANGUAGE_PT
    lang_dir.mkdir(parents=True, exist_ok=True)
    html_path = lang_dir / "carousel.html"
    html_path.write_text(pt_html, encoding=ENCODING_UTF8)
    return str(html_path)


CAPTION_PT = (
    "A Anthropic lançou o Claude Fable 5 e o Claude Mythos 5, dois modelos do "
    "projeto Glassglowing com foco em cibersegurança ofensiva e defensiva.\n\n"
    "Deslize para entender o que muda com o Fable 5, o benchmark do Mythos 5 "
    "e por que as salvaguardas importam antes do deploy.\n\n"
    "#Claude #Anthropic #Cibersegurança #IA #Fable5 #Mythos5 #Glassglowing"
)

# On-topic scenes: AI security ops only — no rockets, vehicles, or celebrity silhouettes.
IMAGE_PROMPTS: dict[int, str] = {
    1: (
        "Futuristic cybersecurity operations center with two glowing holographic AI "
        "model cores labeled abstractly as dual shields, cascading encrypted data "
        "streams, threat maps on wall displays, hooded analyst silhouettes from "
        "behind only, neon orange and cyan lighting"
    ),
    2: (
        "Developer workstation with holographic panels showing AI-assisted code review, "
        "security linting dashboards, and workflow automation nodes, no readable text, "
        "dark cyberpunk server room ambiance"
    ),
    3: (
        "Transparent holographic blueprint of two interconnected neural model "
        "architectures inside a secure data center, glassglowing-style circuit "
        "pathways, risk-control overlays, no rockets or spacecraft"
    ),
    4: (
        "Security operations center with exploit-tree visualizations, defensive "
        "firewall topology maps, and red-team versus blue-team holographic displays, "
        "emphasis on AI threat analysis, no celebrity faces"
    ),
    5: (
        "Layered AI safeguard checkpoint with code streams passing through scanning "
        "gates and policy shields before release, structured validation lights, "
        "enterprise server racks, no launch pads or rockets"
    ),
    6: (
        "Engineer reviewing a holographic checklist beside secure coding panels and "
        "AI copilot status widgets in a dark tech lab, practical next-step planning mood"
    ),
}


async def _load_workflow_drafts(project_id: str) -> tuple[list[dict[str, object]], dict[int, dict[str, object]]]:
    settings = get_settings()
    async with AsyncSqliteSaver.from_conn_string(
        settings.carousel_checkpoint_sqlite_path
    ) as checkpointer:
        state = await CarouselWorkflowEngine(checkpointer=checkpointer).get_state(project_id)
    if state is None:
        raise RuntimeError(f"No workflow state for project {project_id}")
    raw_drafts = state.get("slide_drafts")
    if not isinstance(raw_drafts, list):
        raise RuntimeError("Workflow slide_drafts missing")
    drafts = normalize_slide_drafts(
        [slide for slide in raw_drafts if isinstance(slide, dict)]
    )
    for draft in drafts:
        index = int(draft.get("slide_index") or 0)
        prompt = IMAGE_PROMPTS.get(index)
        if prompt:
            draft["image_prompt"] = prompt
    translations = deserialize_translations_en(state.get("translations_en")) or {}
    return drafts, translations


async def _run(project_id: UUID) -> int:
    settings = get_settings()
    setup_logging(debug=settings.debug)
    await init_db(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )
    container = get_container()
    pid = str(project_id)
    drafts, translations = await _load_workflow_drafts(pid)

    async for session in get_session():
        repo = PostgresCarouselRepository(session)
        project = await repo.get_project_by_id(project_id)
        if project is None:
            raise RuntimeError(f"Project not found: {project_id}")

        project.title = PROJECT_TITLE_PT
        project.presentation_policy_version = "hero_lower_third_v1"
        project.caption = CAPTION_PT
        await repo.update_project(project)

        await apply_slide_drafts_to_database(
            SlideDraftsContext(
                db=session,
                project_id=pid,
                outline=[],
                slide_drafts=drafts,
                translations_en=translations,
            )
        )

        slides = [
            unpack_extras(slide)
            for slide in await repo.get_slides_by_project(project_id)
        ]
        output_dir = Path(project.output_dir or "")
        images_dir = output_dir / "images"
        if images_dir.is_dir():
            for image_file in images_dir.glob("slide_*.jpg"):
                image_file.unlink(missing_ok=True)

        await generate_carousel_images(
            session,
            CarouselImageGenerationContext(
                project_id=pid,
                slides=slides,
                image_registry=container.image_provider_registry(),
            ),
        )
        slides = [
            unpack_extras(slide)
            for slide in await repo.get_slides_by_project(project_id)
        ]
        project = await repo.get_project_by_id(project_id)
        if project is None:
            raise RuntimeError(f"Project not found after image generation: {project_id}")
        _optimize_generated_images(images_dir)
        html_path = _write_preview_html(
            project,
            slides,
            output_dir=output_dir,
            strategy_registry=container.strategy_registry(),
        )

        refinement = CarouselRefinementService(
            CarouselRefinementConfig(
                repository=repo,
                llm_service=container.llm_service(),
                image_registry=container.image_provider_registry(),
                export_service=container.export_service(),
                pdf_slide_builder=container.pdf_slide_builder(),
                strategy_registry=container.strategy_registry(),
            )
        )
        updated = await refinement.re_render_slides(project_id)
        updated.status = CarouselStatus.COMPLETED
        await repo.update_project(updated)

        avatar_source = Path("/app/frontend/public/about-pedro.jpg")
        if not avatar_source.is_file():
            avatar_source = Path(__file__).resolve().parents[2] / "frontend/public/about-pedro.jpg"
        avatar_target = output_dir / "images" / "about-pedro.jpg"
        if avatar_source.is_file() and not avatar_target.is_file():
            avatar_target.write_bytes(avatar_source.read_bytes())

        print(f"project_id={project_id}")
        print(f"title={updated.title}")
        print(f"output_dir={updated.output_dir}")
        print(f"preview_html={html_path}")
        print(f"slides={len(slides)}")
        for slide in slides:
            print(
                f"slide_{slide.slide_number}: {slide.heading[:48]} | "
                f"prompt={str(slide.image_prompt)[:72]}..."
            )
        return 0

    await close_db()
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    args = parser.parse_args()
    return asyncio.run(_run(UUID(str(args.project_id))))


if __name__ == "__main__":
    raise SystemExit(main())
