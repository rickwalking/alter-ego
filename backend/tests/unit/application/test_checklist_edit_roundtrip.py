"""Editor edit -> PATCH save -> rendered slide, for a checklist slide.

Feature file: tests/features/carousel_checklist_wysiwyg.feature

The shared fixture ``tests/fixtures/checklist_edit_roundtrip.json`` holds the slide
the backend serves for generated content (``served_slide``), the edits the owner
makes, and the PATCH payload the frontend editor builds from them
(``patch_slide``, asserted by
``frontend/src/modules/editorial/workspace/components/slide-copy-editor.roundtrip.test.tsx``).
Here the generated rows are seeded, the served copy is checked against the fixture,
the payload goes through the real PATCH route and slide-edit service, and the slide
is rendered from the stored rows in PT and EN.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_backend.api.routes.carousels.deps import CarouselSlideEditRouteDeps
from rag_backend.api.routes.carousels.slide_edit import edit_carousel_slides
from rag_backend.api.schemas.carousel_slide_edit import CarouselSlideEditRequest
from rag_backend.application.services.carousel.carousel_repair_projection import (
    localized_from_slides,
)
from rag_backend.application.services.carousel.carousel_slide_edit_service import (
    CarouselSlideEditDeps,
    CarouselSlideEditService,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.nodes.design import run_design
from rag_backend.application.services.carousel.types import (
    slides_data_for_language,
    unpack_extras,
)
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.application.services.carousel_template.role_layouts import (
    checklist_slide_numbers,
)
from rag_backend.application.services.carousel_template.strategies.registry import (
    bootstrap_strategies,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.models.carousel import (
    CarouselProjectModel,
    CarouselSlideModel,
)
from rag_backend.infrastructure.database.models.event_outbox import EventOutboxModel
from rag_backend.infrastructure.database.models.workflow_audit_log import (
    WorkflowAuditLogModel,
)

pytestmark = pytest.mark.usefixtures("no_outbox_relay")

_FIXTURE = Path(__file__).parents[2] / "fixtures" / "checklist_edit_roundtrip.json"
_ACCESS_TARGET = (
    "rag_backend.api.routes.carousels.slide_edit.get_carousel_project_for_workflow_user"
)
_CHECKLIST_SLIDE = 2
_GENERATED_PT = [
    {"icon_name": "check", "title": "Revise o escopo", "body": "Detalhe gerado um"},
    {"icon_name": "check", "title": "Teste o fluxo", "body": "Detalhe gerado dois"},
]
_GENERATED_EN = [
    {"icon_name": "check", "title": "Review the scope", "body": "Generated detail one"},
    {"icon_name": "check", "title": "Test the flow", "body": "Generated detail two"},
]


class _ParkedCheckpoint:
    async def patch_parked_checkpoint(
        self, project_id: str, values: dict[str, object]
    ) -> bool:
        del project_id, values
        return True


def _factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_rows(test_engine: AsyncEngine) -> AsyncIterator[None]:
    yield
    async with _factory(test_engine)() as db:
        await db.execute(delete(EventOutboxModel))
        await db.execute(delete(WorkflowAuditLogModel))
        await db.execute(delete(CarouselSlideModel))
        await db.execute(delete(CarouselProjectModel))
        await db.commit()


def _fixture() -> dict[str, object]:
    loaded = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _slide_row(project_id: str, number: int, slide_type: str) -> CarouselSlideModel:
    extras: dict[str, object] | None = None
    if number == _CHECKLIST_SLIDE:
        extras = {
            "summary_points": _GENERATED_PT,
            "translation_en": {
                "heading": "Save this",
                "body": "",
                "summary_points": _GENERATED_EN,
            },
        }
    return CarouselSlideModel(
        id=str(uuid.uuid4()),
        project_id=project_id,
        slide_number=number,
        slide_type=slide_type,
        heading="Salve isto" if number == _CHECKLIST_SLIDE else f"Slide {number}",
        body="" if number == _CHECKLIST_SLIDE else f"Corpo {number}",
        extras=extras,
    )


async def _seed(db: AsyncSession) -> CarouselProjectModel:
    project = CarouselProjectModel(
        id=str(uuid.uuid4()),
        topic="Checklist",
        audience="Devs",
        niche="Tech",
        status="completed",
        current_phase="final_review",
        phase_status="approved",
        lock_version=1,
        slide_layout_strategy="save_checklist",
    )
    db.add(project)
    await db.flush()
    for number, slide_type in enumerate(("intro", "summary", "cta"), start=1):
        db.add(_slide_row(str(project.id), number, slide_type))
    await db.commit()
    return project


def _render(project: CarouselProject, rows: list[CarouselSlideModel], lang: str) -> str:
    slides = slides_data_for_language(
        [unpack_extras(row.to_entity()) for row in rows], lang
    )
    return run_design(
        project,
        slides,
        template=CarouselTemplateBuilder(),
        language=lang,
        strategy_registry=bootstrap_strategies(),
    )


async def _rows(db: AsyncSession, project_id: str) -> list[CarouselSlideModel]:
    result = await db.scalars(
        select(CarouselSlideModel)
        .where(CarouselSlideModel.project_id == project_id)
        .order_by(CarouselSlideModel.slide_number)
    )
    return list(result)


@pytest.mark.asyncio
async def test_editor_edit_saved_through_patch_renders_on_the_slide(
    test_engine: AsyncEngine,
) -> None:
    """Scenario: An edited checklist item renders on the slide."""
    fixture = _fixture()
    async with _factory(test_engine)() as db:
        project = await _seed(db)
        entity = project.to_entity()
        rows = await _rows(db, str(project.id))
        stored = [row.to_entity() for row in rows]
        types = {slide.slide_number: slide.slide_type for slide in stored}
        assert checklist_slide_numbers(entity, types) == {_CHECKLIST_SLIDE}
        served = localized_from_slides(stored)
        assert served[_CHECKLIST_SLIDE - 1] == fixture["served_slide"]
        for lang, generated in (("pt", "Revise o escopo"), ("en", "Review the scope")):
            assert generated in _render(entity, rows, lang)

        service = CarouselSlideEditService(
            CarouselSlideEditDeps(
                db=db,
                workflow_service=cast(EditorialWorkflowService, _ParkedCheckpoint()),
                repo=PostgresCarouselRepository(db),
            )
        )
        request = CarouselSlideEditRequest.model_validate({
            "edited_slides": [fixture["patch_slide"]]
        })
        deps = CarouselSlideEditRouteDeps(
            db=db, service=service, current_user=MagicMock(id=uuid.uuid4())
        )
        with patch(_ACCESS_TARGET, return_value=project):
            await edit_carousel_slides(entity.id, request, deps)

        db.expire_all()
        rows = await _rows(db, str(entity.id))
        pt_html = _render(entity, rows, "pt")
        en_html = _render(entity, rows, "en")

    edits = fixture["edits"]
    assert isinstance(edits, list)
    edited = {edit["locale"]: edit["value"] for edit in edits}
    assert edited["presentation_pt"] in pt_html
    assert edited["presentation_en"] in en_html
    assert "Revise o escopo" not in pt_html
    assert "Review the scope" not in en_html
    assert "Teste o fluxo" in pt_html
    assert "Test the flow" in en_html
