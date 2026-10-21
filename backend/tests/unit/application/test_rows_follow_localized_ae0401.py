"""The slide rows render the validated localized copy.

Gherkin: tests/features/slide_copy_validators_ae0401.feature (rows scenarios)
and tests/features/autopilot_slide_autofix_ae0401.feature.
"""

from __future__ import annotations

import copy
from typing import cast
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.carousel_repair_projection import (
    localized_from_slides,
)
from rag_backend.application.services.carousel.editorial_distribution_persist import (
    SlideDraftsContext,
    apply_slide_drafts_to_database,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.localized_rows_sync import (
    localized_records,
    sync_rows_to_localized,
)
from rag_backend.application.services.carousel.owner_autofix_text import (
    lowercase_nouns,
)
from rag_backend.application.services.carousel.owner_autofix_vocabulary import (
    VocabularySources,
    build_vocabulary,
)
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
    PhaseArtifactRunnerConfig,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    validate_localized_slides,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_workflow import PHASE_DESIGN
from tests.unit.application.copy_hygiene_fixtures_ae0401 import POV, prod_deck, pt
from tests.unit.application.owner_autofix_fixtures_ae0367 import (
    V3,
    rows,
    seed_carousel,
)

LONG_DRAFT_TEXT = (
    "Primeiro parágrafo longo do rascunho \u2014 com travessão e texto.\n\n" * 8
)
SHORT_BODY = "O Argon resiste a ataques indiretos hoje."


async def _localized(db: AsyncSession, project_id: str) -> list[dict[str, object]]:
    return localized_from_slides(await rows(db, project_id))


@pytest.mark.unit
@pytest.mark.asyncio
class TestRowsFollowLocalizedCopy:
    async def test_long_draft_text_is_replaced_by_the_localized_body(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: A long draft_text plus short localized copy renders the short copy."""
        project_id = await seed_carousel(db_session)
        localized = await _localized(db_session, project_id)
        draft = {
            "slide_index": 3,
            "title": "Ponto de conteúdo número 3",
            "slide_type": "content",
            "draft_text": LONG_DRAFT_TEXT,
        }
        await apply_slide_drafts_to_database(
            SlideDraftsContext(
                db=db_session,
                project_id=project_id,
                outline=[{"slide_index": 3}],
                slide_drafts=[draft],
                translations_en={},
            )
        )
        row = next(r for r in await rows(db_session, project_id) if r.slide_number == 3)
        assert len(row.body) > 300
        cast(dict[str, object], localized[2]["presentation_pt"])["body"] = SHORT_BODY
        written = await sync_rows_to_localized(
            db_session, project_id, {"localized_slides": localized}
        )
        assert 3 in written
        row = next(r for r in await rows(db_session, project_id) if r.slide_number == 3)
        assert row.body == SHORT_BODY
        report = validate_localized_slides(
            await _localized(db_session, project_id), policy_version=V3
        )
        assert report.blocking is False

    async def test_design_ensure_projects_the_rows(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: Every (re)built localized copy is projected onto the rows."""
        project_id = await seed_carousel(db_session)
        localized = await _localized(db_session, project_id)
        cast(dict[str, object], localized[2]["presentation_pt"])["body"] = SHORT_BODY
        runner = PhaseArtifactRunner(
            PhaseArtifactRunnerConfig(
                outline_agent=MagicMock(),
                content_agent=MagicMock(),
                llm=MagicMock(),
                db=db_session,
                workflow_input=EditorialWorkflowStartInput(
                    topic="t", audience="a", brief="b", sources=[]
                ),
            )
        )
        state = {
            "project_id": project_id,
            "current_phase": PHASE_DESIGN,
            "presentation_policy_version": V3,
            "localized_slides": localized,
        }
        await runner.ensure_for_phase(cast(CarouselWorkflowState, state))
        row = next(r for r in await rows(db_session, project_id) if r.slide_number == 3)
        assert row.body == SHORT_BODY

    async def test_empty_en_lists_match_a_pt_without_the_key(
        self, db_session: AsyncSession
    ) -> None:
        """Scenario: Empty item lists are treated the same on PT and EN."""
        project_id = await seed_carousel(db_session)
        localized = await _localized(db_session, project_id)
        for slide in localized[2:5]:
            cast(dict[str, object], slide["presentation_pt"]).pop("features", None)
            cast(dict[str, object], slide["presentation_en"])["features"] = []
            cast(dict[str, object], slide["presentation_pt"])["content_kind"] = None
            cast(dict[str, object], slide["presentation_en"])["content_kind"] = None
        await sync_rows_to_localized(
            db_session, project_id, {"localized_slides": localized}
        )
        report = validate_localized_slides(
            await _localized(db_session, project_id), policy_version=V3
        )
        codes = {violation.code for violation in report.violations}
        assert "translation_shape_mismatch" not in codes
        for row in (await rows(db_session, project_id))[2:5]:
            extras = row.extras or {}
            translation = cast(dict[str, object], extras.get("translation_en") or {})
            assert "features" not in extras
            assert "features" not in translation

    async def test_nothing_to_sync(self, db_session: AsyncSession) -> None:
        assert await sync_rows_to_localized(None, "p", {"localized_slides": [{}]}) == ()
        assert await sync_rows_to_localized(db_session, "", {}) == ()
        assert localized_records({"localized_slides": "bad"}) == []


@pytest.mark.unit
class TestProperNounPhrases:
    """Scenario: "the code" is not a lowercased "Claude Code"."""

    def _vocabulary(self) -> tuple[str, ...]:
        return build_vocabulary(
            VocabularySources(
                copy=(
                    "No Claude Code eu peço testes antes.",
                    "O Grok Bot publica sozinho.",
                    "Eu uso o Argon, Gemini e outros.",
                )
            )
        )

    def test_phrases_are_learned_whole(self) -> None:
        vocabulary = self._vocabulary()
        assert "Claude Code" in vocabulary
        assert "Grok Bot" in vocabulary
        assert "Code" not in vocabulary
        assert "Bot" not in vocabulary
        assert {"Argon", "Gemini"} <= set(vocabulary)

    def test_only_the_full_phrase_is_flagged(self) -> None:
        vocabulary = self._vocabulary()
        assert lowercase_nouns("I read the code and the bot runs.", vocabulary) == ()
        assert lowercase_nouns("I use claude code daily.", vocabulary) == (
            "claude code",
        )
        assert lowercase_nouns("The grok bot posts.", vocabulary) == ("grok bot",)


@pytest.mark.unit
class TestHookFitsThePhoto:
    """Scenario: The POV hook sub-line stays on one short line."""

    def test_long_hook_subline_is_blocked(self) -> None:
        deck = copy.deepcopy(prod_deck())
        pt(deck, 1)["body"] = "E isso custa caro no fim de todo sprint do time"
        report = validate_localized_slides(deck, policy_version=POV)
        assert (1, "body_too_long") in {
            (v.slide_index, v.code) for v in report.violations
        }

    def test_short_hook_subline_passes(self) -> None:
        report = validate_localized_slides(prod_deck(), policy_version=POV)
        assert report.violations == []
