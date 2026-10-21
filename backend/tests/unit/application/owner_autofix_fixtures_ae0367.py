"""Prod-shaped carousel at final review for the owner autofix flow tests.

``seed_carousel`` persists the valid 7-slide carousel through the real
content persist path; ``break_carousel`` then writes the owner-reported
defects straight onto the rows (as on carousels drafted before the quality fixes):
slide 3 mangled ``strong ... /strong``, slide 4 title-only, slide 5 lowercase
heading with "argon" lowercased, slide 6 EN still Portuguese.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from uuid import UUID

from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.carousel_repair_projection import (
    localized_from_slides,
)
from rag_backend.application.services.carousel.editorial_distribution_persist import (
    SlideDraftsContext,
    apply_slide_drafts_to_database,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.presentation_casing_markers import (
    CASING_REPAIRS_KEY,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_FINAL_REVIEW
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V3,
)
from rag_backend.domain.models.carousel import CarouselSlide
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from tests.unit.application.content_quality_fixtures_ae0366 import clean_drafts

V3 = PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V3
LOCK_VERSION = 3
IMAGE_PATH = "/tmp/ae0367/slide_{n}.jpg"
BROKEN_HEADING_5 = "a versão para robótica leva o argon ao mundo físico"
FIXED_HEADING_5 = "A versão para robótica leva o Argon ao mundo físico"
MANGLED_BODY_3 = "O Argon resiste a strongindirect prompt injections/strong hoje."
FIXED_BODY_3 = "O Argon resiste a <strong>indirect prompt injections</strong> hoje."
PT_BODY_6 = "Teste o modelo hoje com os seus próprios prompts."
KEY_POINTS_4 = (
    "Simulação Real2Sim: treina no mundo virtual antes do real",
    "Braços robóticos: seguem instruções em linguagem natural",
    "Parada segura: o robô para quando algo sai do esperado",
)
_IDS = re.compile(r'"id": "([^"]+)"')


@dataclass
class FakeChatModel:
    """Answers the re-translate prompt with English for every id it was sent."""

    fail: bool = False
    calls: int = 0
    ids: list[str] = field(default_factory=list)

    async def ainvoke(self, messages: list[object], config: object = None) -> object:
        del config
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider down")
        prompt = str(getattr(messages[0], "content", ""))
        ids = _IDS.findall(prompt)
        self.ids.extend(ids)
        answer = {"translations": [{"id": i, "text": f"english copy {i}"} for i in ids]}
        import json

        return _Reply(content=json.dumps(answer))


@dataclass
class _Reply:
    content: str


async def seed_carousel(db: AsyncSession) -> str:
    """A completed v3 carousel at final review with its 7 rows and images."""
    project = CarouselProjectModel(
        id=str(uuid.uuid4()),
        topic="Gemini 4 Argon chegou",
        audience="Devs",
        niche="Tech",
        status="completed",
        current_phase=PHASE_FINAL_REVIEW,
        phase_status="awaiting_human",
        lock_version=LOCK_VERSION,
        presentation_policy_version=V3,
        output_dir="/tmp/ae0367",
    )
    db.add(project)
    await db.flush()
    project_id = str(project.id)
    drafts = clean_drafts()
    await apply_slide_drafts_to_database(
        SlideDraftsContext(
            db=db,
            project_id=project_id,
            outline=[{"slide_index": draft["slide_index"]} for draft in drafts],
            slide_drafts=drafts,
            translations_en={},
        )
    )
    for row in await rows(db, project_id):
        row.image_path = IMAGE_PATH.format(n=row.slide_number)
        await PostgresCarouselRepository(session=db).update_slide(row)
    return project_id


async def rows(db: AsyncSession, project_id: str) -> list[CarouselSlide]:
    repo = PostgresCarouselRepository(session=db)
    return await repo.get_slides_by_project(UUID(project_id))


async def row(db: AsyncSession, project_id: str, number: int) -> CarouselSlide:
    return next(r for r in await rows(db, project_id) if r.slide_number == number)


def _translation(slide: CarouselSlide) -> dict[str, object]:
    extras = dict(slide.extras or {})
    raw = extras.get("translation_en")
    return dict(raw) if isinstance(raw, dict) else {}


async def _save(
    db: AsyncSession, slide: CarouselSlide, translation: dict[str, object]
) -> None:
    extras = dict(slide.extras or {})
    extras["translation_en"] = translation
    slide.extras = extras
    await PostgresCarouselRepository(session=db).update_slide(slide)


async def break_carousel(db: AsyncSession, project_id: str) -> None:
    """Write the owner-reported defects onto slides 3-6."""
    slide3 = await row(db, project_id, 3)
    slide3.body = MANGLED_BODY_3
    await _save(db, slide3, _translation(slide3))
    slide4 = await row(db, project_id, 4)
    slide4.body = ""
    extras = dict(slide4.extras or {})
    extras.pop("features", None)
    slide4.extras = extras
    translation = _translation(slide4)
    translation.update({"body": "", "features": []})
    await _save(db, slide4, translation)
    slide5 = await row(db, project_id, 5)
    slide5.heading = BROKEN_HEADING_5
    await _save(db, slide5, _translation(slide5))
    slide6 = await row(db, project_id, 6)
    slide6.body = PT_BODY_6
    translation = _translation(slide6)
    translation.update({"heading": slide6.heading, "body": PT_BODY_6})
    await _save(db, slide6, translation)


def _outline() -> list[dict[str, object]]:
    types = ("intro", "summary", "content", "content", "content", "closing", "cta")
    outline: list[dict[str, object]] = [
        {
            "slide_index": index,
            "title": f"Ponto {index} do Argon",
            "key_points": [f"Detalhe {index}: o Argon na prática"],
            "slide_type": slide_type,
        }
        for index, slide_type in enumerate(types, start=1)
    ]
    outline[3]["key_points"] = list(KEY_POINTS_4)
    outline[4]["title"] = FIXED_HEADING_5
    return outline


async def seed_checkpoint(
    engine: EditorialWorkflowService, db: AsyncSession, project_id: str
) -> None:
    """Final-review checkpoint: outline, research, presentation copy + markers.

    Seeding reaches into the inner graph engine; this is for fresh test threads only.
    """
    localized = localized_from_slides(await rows(db, project_id))
    localized[4][CASING_REPAIRS_KEY] = [
        {"locale": "pt", "field": "heading", "code": "heading_not_sentence_case_pt"}
    ]
    state: dict[str, object] = {
        "project_id": project_id,
        "current_phase": PHASE_FINAL_REVIEW,
        "phase_status": "awaiting_human",
        "presentation_policy_version": V3,
        "outline": _outline(),
        "research_findings": [
            {
                "title": "Gemini 4 Argon Takes Robots Into The Physical World",
                "summary": "",
            }
        ],
        "localized_slides": localized,
    }
    graph = engine._orchestrator._engine
    await graph.update_state(project_id, state, as_node=PHASE_FINAL_REVIEW)


def build_engine(llm: FakeChatModel) -> EditorialWorkflowService:
    """The real editorial engine on an in-memory checkpointer and a fake model."""
    from typing import cast

    from langchain_core.language_models import BaseChatModel

    return EditorialWorkflowService(
        EditorialWorkflowConfig(
            llm=cast(BaseChatModel, llm), checkpointer=MemorySaver()
        )
    )
