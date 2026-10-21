"""Reviewer edits reach the persisted slide rows and the render.

Prod carousel 8e350d6e: the reviewer fixed slide 5 at the content gate, but
``carousel_slides`` kept the old lowercase copy, so the JPGs did too.

Gherkin: tests/features/carousel_content_quality_ae0366.feature
"""

from __future__ import annotations

import copy
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.edited_slide_persist import (
    EditedSlidePersistCommand,
    persist_edited_slide_copy,
)
from rag_backend.application.services.carousel.editorial_distribution_persist import (
    SlideDraftsContext,
    apply_slide_drafts_to_database,
)
from rag_backend.application.services.carousel.editorial_workflow_service import (
    EditorialWorkflowConfig,
    EditorialWorkflowService,
)
from rag_backend.application.services.carousel.editorial_workflow_types import (
    ResumeWorkflowInput,
)
from rag_backend.application.services.carousel.nodes.design import run_design
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    build_presentation_review_updates,
)
from rag_backend.application.services.carousel.types import unpack_extras
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_BRIEF,
    PHASE_CONTENT,
    PHASE_FINAL_REVIEW,
    REVIEW_ACTION_REVISE,
    STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V3,
)
from rag_backend.domain.models.carousel import CarouselSlide
from rag_backend.infrastructure.database.carousel_repository import (
    PostgresCarouselRepository,
)
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from tests.unit.application.content_quality_fixtures_ae0366 import (
    FIXED_HEADING_5,
    LOWERCASE_HEADING_5,
    SLIDE5_INDEX,
    clean_drafts,
    prod_drafts,
)

_V3 = PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V3
_SERVICE = "rag_backend.application.services.carousel.editorial_workflow_service"
_EDITED_HEADING = "A versão para robótica leva o Argon ao mundo físico"
_EDITED_BODY = "O Argon agora controla <strong>braços robóticos</strong> reais."
_EDITED_EN_HEADING = "The robotics version takes Argon into the physical world"
_EDITED_EN_BODY = "Argon now drives real <strong>robot arms</strong>."
_EDITED_FEATURE = "Simulação Real2Sim"
_IMAGE_PATH = "/tmp/images/slide_5.jpg"


async def _project(db: AsyncSession) -> str:
    project = CarouselProjectModel(
        id=str(uuid.uuid4()),
        topic="Gemini 4 Argon chegou",
        audience="Devs",
        niche="Tech",
        status="drafting",
        current_phase=PHASE_CONTENT,
        phase_status="awaiting_human",
        lock_version=1,
        presentation_policy_version=_V3,
    )
    db.add(project)
    await db.flush()
    return str(project.id)


async def _persist_prod_rows(db: AsyncSession, project_id: str) -> None:
    """Content-phase persist of the prod drafts, then an image on slide 5."""
    drafts = prod_drafts()
    drafts[SLIDE5_INDEX - 1]["long_form_notes"] = "Notas longas do slide."
    await apply_slide_drafts_to_database(
        SlideDraftsContext(
            db=db,
            project_id=project_id,
            outline=[{"slide_index": d["slide_index"]} for d in drafts],
            slide_drafts=drafts,
            translations_en={},
        )
    )
    repo = PostgresCarouselRepository(session=db)
    slide5 = await _row(db, project_id, SLIDE5_INDEX)
    slide5.image_path = _IMAGE_PATH
    await repo.update_slide(slide5)


async def _row(db: AsyncSession, project_id: str, number: int) -> CarouselSlide:
    repo = PostgresCarouselRepository(session=db)
    rows = await repo.get_slides_by_project(UUID(project_id))
    return next(row for row in rows if row.slide_number == number)


def _prior_state(phase: str) -> dict[str, object]:
    drafts = prod_drafts()
    return {
        "current_phase": phase,
        "presentation_policy_version": _V3,
        "slide_drafts": drafts,
        **build_presentation_review_updates(drafts, policy_version=_V3),
    }


def _slide5_edit() -> dict[str, object]:
    clean = copy.deepcopy(clean_drafts()[SLIDE5_INDEX - 1])
    pt = clean["presentation_pt"]
    en = clean["presentation_en"]
    assert isinstance(pt, dict)
    assert isinstance(en, dict)
    pt.update({"heading": _EDITED_HEADING, "body": _EDITED_BODY})
    pt["features"][0]["title"] = _EDITED_FEATURE
    en.update({"heading": _EDITED_EN_HEADING, "body": _EDITED_EN_BODY})
    return {
        "slide_index": SLIDE5_INDEX,
        "slide_type": "content",
        "presentation_pt": pt,
        "presentation_en": en,
    }


async def _persist_edit(
    db: AsyncSession, project_id: str, phase: str
) -> tuple[int, ...]:
    return await persist_edited_slide_copy(
        EditedSlidePersistCommand(
            db=db,
            project_id=project_id,
            prior=_prior_state(phase),
            structured_feedback={
                STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY: [_slide5_edit()]
            },
        )
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestPersistMappingRepairsCasing:
    """Scenario: the persisted rows carry the repaired (validated) copy."""

    async def test_content_persist_capitalizes_rows(
        self, db_session: AsyncSession
    ) -> None:
        """Only the first letter is capitalized: "api" is not a configured noun, so it
        is kept.
        """
        project_id = await _project(db_session)
        await _persist_prod_rows(db_session, project_id)

        slide5 = await _row(db_session, project_id, SLIDE5_INDEX)
        slide6 = await _row(db_session, project_id, 6)

        assert slide5.heading == FIXED_HEADING_5
        assert slide5.heading != LOWERCASE_HEADING_5
        assert slide6.heading == "O que muda para devs no Brasil"
        features = (slide6.extras or {})["features"]
        assert isinstance(features, list)
        assert features[0]["title"] == "Teste a api"


@pytest.mark.unit
@pytest.mark.asyncio
class TestEditedCopyReachesRows:
    """Scenario: an edit at content/design/final_review rewrites the slide rows."""

    @pytest.mark.parametrize("phase", [PHASE_CONTENT, PHASE_FINAL_REVIEW])
    async def test_edit_rewrites_heading_body_features_and_en(
        self, db_session: AsyncSession, phase: str
    ) -> None:
        """Images, prompts and long-form notes are untouched by a copy edit."""
        project_id = await _project(db_session)
        await _persist_prod_rows(db_session, project_id)

        updated = await _persist_edit(db_session, project_id, phase)

        assert updated == (SLIDE5_INDEX,)
        slide5 = await _row(db_session, project_id, SLIDE5_INDEX)
        extras = slide5.extras or {}
        assert slide5.heading == _EDITED_HEADING
        assert slide5.body == _EDITED_BODY
        features = extras["features"]
        assert isinstance(features, list)
        assert features[0]["title"] == _EDITED_FEATURE
        translation = extras["translation_en"]
        assert isinstance(translation, dict)
        assert translation["heading"] == _EDITED_EN_HEADING
        assert translation["body"] == _EDITED_EN_BODY
        assert slide5.image_path == _IMAGE_PATH
        assert extras["long_form_notes"] == "Notas longas do slide."
        assert extras["image_prompt"] == "Editorial illustration 5"

    async def test_render_after_edit_uses_the_new_copy(
        self, db_session: AsyncSession
    ) -> None:
        project_id = await _project(db_session)
        await _persist_prod_rows(db_session, project_id)
        await _persist_edit(db_session, project_id, PHASE_CONTENT)
        repo = PostgresCarouselRepository(session=db_session)
        project = await repo.get_project_by_id(UUID(project_id))
        assert project is not None
        rows = await repo.get_slides_by_project(UUID(project_id))

        html = run_design(
            project,
            [unpack_extras(row) for row in rows],
            template=CarouselTemplateBuilder(),
        )

        assert _EDITED_HEADING in html
        assert "braços robóticos" in html
        assert LOWERCASE_HEADING_5 not in html

    async def test_unedited_rows_and_other_phases_are_untouched(
        self, db_session: AsyncSession
    ) -> None:
        project_id = await _project(db_session)
        await _persist_prod_rows(db_session, project_id)
        before = (await _row(db_session, project_id, 3)).heading

        assert await _persist_edit(db_session, project_id, PHASE_BRIEF) == ()
        assert (await _row(db_session, project_id, SLIDE5_INDEX)).heading == (
            FIXED_HEADING_5
        )
        await _persist_edit(db_session, project_id, PHASE_CONTENT)
        assert (await _row(db_session, project_id, 3)).heading == before

    async def test_no_edits_or_no_db_is_a_no_op(self, db_session: AsyncSession) -> None:
        command = EditedSlidePersistCommand(
            db=db_session,
            project_id=str(uuid.uuid4()),
            prior=_prior_state(PHASE_CONTENT),
            structured_feedback={STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY: []},
        )
        assert await persist_edited_slide_copy(command) == ()
        no_db = EditedSlidePersistCommand(
            db=None,
            project_id="x",
            prior=_prior_state(PHASE_CONTENT),
            structured_feedback={
                STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY: [_slide5_edit()]
            },
        )
        assert await persist_edited_slide_copy(no_db) == ()


@pytest.mark.unit
@pytest.mark.asyncio
class TestDraftPersistUsesPresentationCopy:
    """Scenario: drafts persist from presentation copy, not stale draft fields."""

    async def test_edited_presentation_wins_over_stale_fields(
        self, db_session: AsyncSession
    ) -> None:
        """An empty presentation body resurrects no stale draft_text."""
        project_id = await _project(db_session)
        draft = copy.deepcopy(clean_drafts()[SLIDE5_INDEX - 1])
        edit = _slide5_edit()
        draft.update({
            "title": LOWERCASE_HEADING_5,
            "draft_text": "texto velho em minúsculas",
            "presentation_pt": edit["presentation_pt"],
            "presentation_en": edit["presentation_en"],
        })
        draft["presentation_pt"]["body"] = ""

        await apply_slide_drafts_to_database(
            SlideDraftsContext(
                db=db_session,
                project_id=project_id,
                outline=[{"slide_index": SLIDE5_INDEX}],
                slide_drafts=[draft],
                translations_en={
                    SLIDE5_INDEX: {"heading": "old en", "body": "old en body"}
                },
            )
        )

        row = await _row(db_session, project_id, SLIDE5_INDEX)
        translation = (row.extras or {})["translation_en"]
        assert isinstance(translation, dict)
        assert row.heading == _EDITED_HEADING
        assert row.body == ""
        assert translation["heading"] == _EDITED_EN_HEADING
        assert translation["body"] == _EDITED_EN_BODY


@pytest.mark.unit
@pytest.mark.asyncio
class TestResumePersistsEditsFirst:
    """Scenario: resume projects the edits before the graph moves on."""

    async def test_resume_persists_edits_before_the_graph_resumes(self) -> None:
        calls: list[str] = []
        prior = _prior_state(PHASE_CONTENT)
        orchestrator = MagicMock()
        orchestrator.get_state = AsyncMock(return_value=prior)
        orchestrator.engine.update_state = AsyncMock()
        orchestrator.update_state = AsyncMock()

        async def _resume(*_args: object, **_kwargs: object) -> dict[str, object]:
            calls.append("resume")
            return prior

        async def _persist(command: EditedSlidePersistCommand) -> tuple[int, ...]:
            calls.append("persist")
            assert command.structured_feedback is feedback
            return (SLIDE5_INDEX,)

        orchestrator.resume = _resume
        service = EditorialWorkflowService(EditorialWorkflowConfig(llm=MagicMock()))
        service._orchestrator = orchestrator
        feedback: dict[str, object] = {
            STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY: [_slide5_edit()]
        }
        with patch(f"{_SERVICE}.persist_edited_slide_copy", side_effect=_persist):
            await service.resume_workflow(
                ResumeWorkflowInput(
                    project_id=str(uuid.uuid4()),
                    action=REVIEW_ACTION_REVISE,
                    reviewer_id="owner",
                    feedback="fix casing",
                    structured_feedback=feedback,
                )
            )

        assert calls[:2] == ["persist", "resume"]
