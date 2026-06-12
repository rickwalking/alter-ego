#!/usr/bin/env python3
"""Tighten carousel slide copy and re-render without regenerating images."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from uuid import UUID

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from rag_backend.agents.carousel_workflow_engine import CarouselWorkflowEngine
from rag_backend.application.services.carousel.malformed_draft_normalizer import (
    normalize_slide_drafts,
)
from rag_backend.application.services.carousel.presentation_review import (
    build_presentation_review_updates,
    deserialize_translations_en,
    serialize_translations_en,
)
from rag_backend.application.services.carousel.refinement_service import (
    CarouselRefinementConfig,
    CarouselRefinementService,
)
from rag_backend.domain.models.carousel import CarouselStatus
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.container import get_container
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.config import close_db, get_session, init_db
from rag_backend.infrastructure.logging import setup_logging

PROJECT_ID = "eeaf0d66-1130-41b3-9c16-7ded632b8821"

# Compact lower-third copy modeled on f2231ece: short title + 2-3 tight lines.
# Use **bold** (not <strong>) so _render_inline emits proper emphasis tags.
SLIDE_COPY_PT: dict[int, dict[str, str]] = {
    1: {
        "heading": "Fable 5 e Mythos 5 chegaram juntos",
        "body": (
            "Nascidos do projeto Glassglowing, os dois modelos entram com foco em "
            "cibersegurança ofensiva e defensiva.\n\n"
            "O salto: capacidades avançadas com governança antes do lançamento."
        ),
    },
    2: {
        "heading": "O que você vai aprender aqui",
        "body": (
            "Fable 5 e Mythos 5 sob o projeto Glassglowing.\n"
            "Mythos 5 como referência em segurança ofensiva e defensiva.\n"
            "Fable 5 com salvaguardas estruturadas antes do deploy."
        ),
    },
    3: {
        "heading": "Projeto Glassglowing",
        "body": (
            "Mesma família Anthropic, com **controle de riscos** desde a base.\n"
            "Dois modelos, duas estratégias de lançamento.\n"
            "Foco total em cibersegurança ofensiva e defensiva."
        ),
    },
    4: {
        "heading": "Referência em cibersegurança",
        "body": (
            "Mythos 5 supera modelos existentes em testes ofensivos e defensivos.\n"
            "Posicionado como **referência do setor** após avaliação rigorosa.\n"
            "Alto potencial exigiu revisão de risco antes da disponibilização."
        ),
    },
    5: {
        "heading": "Fable 5: salvaguardas antes do lançamento",
        "body": (
            "Diferente do Mythos 5, o Fable 5 passou por salvaguardas estruturadas.\n"
            "Riscos iniciais eliminados antes do lançamento público.\n"
            "Capacidades avançadas com **segurança validada** na entrega."
        ),
    },
    6: {
        "heading": "Próximos passos",
        "body": (
            "Compare Fable 5 e Mythos 5 no seu contexto de segurança.\n"
            "Teste casos reais antes de escalar automação.\n"
            "Revise sempre código e políticas com supervisão humana."
        ),
    },
    7: {
        "heading": "Fique por dentro",
        "body": (
            "Salve este carrossel e siga o perfil para acompanhar novidades sobre "
            "**modelos de IA avançados**."
        ),
    },
}

SLIDE_COPY_EN: dict[int, dict[str, str]] = {
    1: {
        "heading": "Fable 5 and Mythos 5 launch together",
        "body": (
            "Born from project Glassglowing, both models launch with a focus on "
            "offensive and defensive cybersecurity.\n\n"
            "The shift: advanced capabilities with governance before release."
        ),
    },
    2: {
        "heading": "What you will learn here",
        "body": (
            "Fable 5 and Mythos 5 under the Glassglowing project.\n"
            "Mythos 5 as the benchmark in offensive and defensive security.\n"
            "Fable 5 with structured safeguards before deployment."
        ),
    },
    3: {
        "heading": "The Glassglowing project",
        "body": (
            "Same Anthropic family, with **risk control** from day one.\n"
            "Two models, two launch strategies.\n"
            "Full focus on offensive and defensive cybersecurity."
        ),
    },
    4: {
        "heading": "The cybersecurity benchmark",
        "body": (
            "Mythos 5 outperforms existing models in offensive and defensive tests.\n"
            "Positioned as the **industry benchmark** after rigorous review.\n"
            "High potential required stricter risk assessment before release."
        ),
    },
    5: {
        "heading": "Fable 5: safeguards before release",
        "body": (
            "Unlike Mythos 5, Fable 5 went through structured safeguards.\n"
            "Initial risks were eliminated before public launch.\n"
            "Advanced capabilities with **validated security** at delivery."
        ),
    },
    6: {
        "heading": "Next steps",
        "body": (
            "Compare Fable 5 and Mythos 5 in your security context.\n"
            "Test real cases before scaling automation.\n"
            "Always review code and policies with human oversight."
        ),
    },
    7: {
        "heading": "Stay in the loop",
        "body": (
            "Save this carousel and follow the profile to keep up with "
            "**advanced AI models**."
        ),
    },
}


def _merge_extras(
    extras: object,
    *,
    slide_number: int,
    clear_structured: bool,
) -> dict[str, object]:
    merged: dict[str, object] = dict(extras) if isinstance(extras, dict) else {}
    en = SLIDE_COPY_EN.get(slide_number)
    if en:
        merged["translation_en"] = en
    if clear_structured:
        merged.pop("summary_points", None)
        merged.pop("features", None)
    if slide_number == 1:
        merged.pop("tldr_strip", None)
    return merged


async def _sync_workflow_checkpoint(project_id: str) -> None:
    settings = get_settings()
    async with AsyncSqliteSaver.from_conn_string(
        settings.carousel_checkpoint_sqlite_path
    ) as checkpointer:
        engine = CarouselWorkflowEngine(checkpointer=checkpointer)
        state = await engine.get_state(project_id)
        if state is None:
            return
        raw_drafts = state.get("slide_drafts")
        if not isinstance(raw_drafts, list):
            return
        drafts = normalize_slide_drafts(
            [slide for slide in raw_drafts if isinstance(slide, dict)]
        )
        for draft in drafts:
            slide_index = int(draft.get("slide_index") or 0)
            copy = SLIDE_COPY_PT.get(slide_index)
            if not copy:
                continue
            draft["title"] = copy["heading"]
            draft["draft_text"] = copy["body"]
            presentation_pt = dict(draft.get("presentation_pt") or {})
            if isinstance(presentation_pt, dict):
                presentation_pt["heading"] = copy["heading"]
                presentation_pt["body"] = copy["body"]
                presentation_pt.pop("tldr_strip", None)
                draft["presentation_pt"] = presentation_pt
            presentation_en = dict(draft.get("presentation_en") or {})
            en_copy = SLIDE_COPY_EN.get(slide_index)
            if isinstance(presentation_en, dict) and en_copy:
                presentation_en["heading"] = en_copy["heading"]
                presentation_en["body"] = en_copy["body"]
                presentation_en.pop("tldr_strip", None)
                draft["presentation_en"] = presentation_en
            draft.pop("summary_points", None)
            draft.pop("features", None)
            draft.pop("tldr_strip", None)

        translations_en = {
            idx: {"heading": item["heading"], "body": item["body"]}
            for idx, item in SLIDE_COPY_EN.items()
        }
        review_updates = build_presentation_review_updates(
            drafts,
            translations_en=translations_en,
            policy_version=str(
                state.get("presentation_policy_version") or "hero_lower_third_v1"
            ),
        )
        as_node = str(state.get("current_phase") or "final_review")
        await engine.update_state(
            project_id,
            {
                "slide_drafts": drafts,
                **review_updates,
                "translations_en": serialize_translations_en(translations_en),
                "phase_status": "approved",
            },
            as_node=as_node,
        )


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

    async for session in get_session():
        repo = PostgresCarouselRepository(session)
        slides = await repo.get_slides_by_project(project_id)
        for slide in slides:
            copy = SLIDE_COPY_PT.get(slide.slide_number)
            if not copy:
                continue
            slide.heading = copy["heading"]
            slide.body = copy["body"]
            slide.extras = _merge_extras(
                slide.extras,
                slide_number=slide.slide_number,
                clear_structured=slide.slide_number in {2, 3, 4, 5, 6},
            )
            await repo.update_slide(slide)

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

        output_dir = Path(updated.output_dir or "")
        repo_root = Path(__file__).resolve().parents[2]
        avatar_candidates = [
            Path("/app/frontend/public/about-pedro.jpg"),
            repo_root / "frontend/public/about-pedro.jpg",
        ]
        avatar_target = output_dir / "images" / "about-pedro.jpg"
        for avatar_source in avatar_candidates:
            if avatar_source.is_file():
                avatar_target.write_bytes(avatar_source.read_bytes())
                break

        await _sync_workflow_checkpoint(pid)

        html_path = output_dir / "pt" / "carousel.html"
        html = html_path.read_text(encoding="utf-8") if html_path.is_file() else ""
        print(f"project_id={project_id}")
        print(f"preview_html={html_path}")
        print(f"json_blobs={html.count(chr(123) + chr(39) + 'pt')}")
        print(f"escaped_strong={html.count('&lt;strong&gt;')}")
        for slide_number, copy in sorted(SLIDE_COPY_PT.items()):
            print(f"slide_{slide_number}: {copy['heading'][:50]} | body={len(copy['body'])}")
        return 0

    await close_db()
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", default=PROJECT_ID)
    args = parser.parse_args()
    return asyncio.run(_run(UUID(str(args.project_id))))


if __name__ == "__main__":
    raise SystemExit(main())
