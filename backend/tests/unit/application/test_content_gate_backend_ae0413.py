"""AE-0413: EN translations, re-draft notes, language check, casing message,
feedback history and research relevance (REPORT B03, B12, B14, B16).

Gherkin: tests/features/content_gate_backend_ae0413.feature
"""

from __future__ import annotations

from typing import ClassVar, cast
from unittest.mock import MagicMock, patch

import pytest

from rag_backend.agents.research_relevance import (
    ResearchHit,
    hit_rejection,
    search_query_for,
)
from rag_backend.api.routes.carousels.editorial_workflow_routes_feedback import (
    phase_feedback_history_field,
)
from rag_backend.application.services.carousel.copy_hygiene_text import (
    wrong_language_detail,
)
from rag_backend.application.services.carousel.editorial_workflow_generators import (
    ContentRegenInputs,
    SlideDraftGenerationParams,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.phase_artifact_runner import (
    PhaseArtifactRunner,
    PhaseArtifactRunnerConfig,
    _review_translations,
)
from rag_backend.application.services.carousel.presentation_casing_markers import (
    CASING_REPAIR_MESSAGE,
)
from rag_backend.application.services.carousel.presentation_content_rules import (
    TranslationCheckCommand,
    translation_violations,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_TRANSLATION_NOT_ENGLISH,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V3,
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V4,
)
from rag_backend.domain.constants.research_enrichment import (
    FILTER_REASON_LANGUAGE,
    FILTER_REASON_OFF_TOPIC,
)

_STORED = {"2": {"heading": "Stored EN heading", "body": "Stored EN body."}}
_FRESH = {"2": {"heading": "Fresh EN heading", "body": "Fresh EN body."}}
_PT_HEADING = "Agentes de código mudam o review"


def _state(**values: object) -> CarouselWorkflowState:
    return cast(CarouselWorkflowState, values)


@pytest.mark.unit
class TestReviewTranslations:
    """Scenario: A content re-entry without regeneration keeps the stored EN translations."""

    def test_stored_translations_apply_without_regeneration(self) -> None:
        assert _review_translations(_state(translations_en=_STORED), {}) == _STORED

    def test_fresh_translations_win(self) -> None:
        updates: dict[str, object] = {"translations_en": _FRESH, "slide_drafts": []}
        assert _review_translations(_state(translations_en=_STORED), updates) == _FRESH

    def test_regenerated_drafts_never_reuse_stale_translations(self) -> None:
        updates: dict[str, object] = {"slide_drafts": [{"slide_index": 2}]}
        assert _review_translations(_state(translations_en=_STORED), updates) is None


def _runner() -> PhaseArtifactRunner:
    return PhaseArtifactRunner(
        PhaseArtifactRunnerConfig(
            outline_agent=MagicMock(),
            content_agent=MagicMock(),
            llm=MagicMock(),
        )
    )


@pytest.mark.unit
class TestRedraftCarriesNotes:
    """Scenario: The fail-closed re-draft carries the reviewer notes."""

    _OUTLINE: ClassVar[list[object]] = [
        {"slide_index": 1, "title": "Gancho", "key_points": []}
    ]
    _INPUT = EditorialWorkflowStartInput(topic="t", audience="a", brief="b", sources=[])

    def _captured(self, regen: ContentRegenInputs | None) -> SlideDraftGenerationParams:
        target = (
            "rag_backend.application.services.carousel.phase_artifact_runner."
            "build_slide_draft_retry"
        )
        with patch(target) as build:
            _runner()._resolve_slide_draft_retry(self._INPUT, self._OUTLINE, regen)
        params = build.call_args.args[1]
        assert isinstance(params, SlideDraftGenerationParams)
        return params

    def test_redraft_receives_the_revision_notes(self) -> None:
        params = self._captured(ContentRegenInputs(revision_notes=["EN em inglês"]))
        assert params.revision_notes == ["EN em inglês"]

    def test_redraft_without_regen_inputs_has_no_notes(self) -> None:
        params = self._captured(None)
        assert params.revision_notes is None
        assert params.mode is None


@pytest.mark.unit
class TestPortugueseEnglishCopy:
    """Scenario: Portuguese EN copy is reported on every content result."""

    def test_short_portuguese_en_heading_reads_as_portuguese(self) -> None:
        assert wrong_language_detail(_PT_HEADING, portuguese=False) == (
            "reads as Portuguese"
        )

    def test_english_heading_is_not_flagged(self) -> None:
        heading = "Code agents change the review"
        assert wrong_language_detail(heading, portuguese=False) == ""

    def test_portuguese_pt_heading_is_not_flagged(self) -> None:
        assert wrong_language_detail(_PT_HEADING, portuguese=True) == ""

    def _codes(self, version: str, en_heading: str) -> list[str]:
        command = TranslationCheckCommand(
            pt_payload={"heading": _PT_HEADING, "body": ""},
            en_payload={"heading": en_heading, "body": ""},
            policy=load_presentation_policy(version),
            slide_index=2,
        )
        return [violation.code for violation in translation_violations(command)]

    def test_v3_reports_portuguese_en_as_not_english(self) -> None:
        codes = self._codes(
            PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V3,
            "Agentes de código no review",
        )
        assert codes == [VIOLATION_TRANSLATION_NOT_ENGLISH]

    def test_v4_leaves_portuguese_en_to_wrong_language(self) -> None:
        codes = self._codes(
            PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V4,
            "Agentes de código no review",
        )
        assert codes == []

    def test_identical_copy_is_still_not_english(self) -> None:
        codes = self._codes(
            PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V4, _PT_HEADING
        )
        assert codes == [VIOLATION_TRANSLATION_NOT_ENGLISH]


@pytest.mark.unit
class TestCasingMessage:
    """Scenario: The sentence-case marker message does not claim an auto-capitalization."""

    def test_message_asks_for_an_edit_and_claims_no_fix(self) -> None:
        assert "auto-capitalized" not in CASING_REPAIR_MESSAGE
        assert "Edit or regenerate" in CASING_REPAIR_MESSAGE


@pytest.mark.unit
class TestFeedbackHistoryField:
    """Scenario: A consumed content note is exposed in the state response."""

    _ENTRY: ClassVar[dict[str, str]] = {
        "note": "EN em inglês",
        "source": "human",
        "added_at": "2026-10-16T10:00:00+00:00",
        "status": "applied",
        "settled_at": "2026-10-16T10:02:00+00:00",
    }

    def test_applied_note_is_exposed(self) -> None:
        state: dict[str, object] = {
            "phase_feedback": {"content": []},
            "phase_feedback_history": {"content": [self._ENTRY], "outline": []},
        }

        history = phase_feedback_history_field(state)

        assert list(history) == ["content"]
        assert history["content"][0].model_dump() == self._ENTRY

    def test_state_response_serves_the_history(self) -> None:
        from rag_backend.api.routes.carousels.editorial_workflow_routes_response import (
            build_editorial_workflow_state_response,
        )

        response = build_editorial_workflow_state_response({
            "project_id": "p",
            "current_phase": "content",
            "phase_status": "awaiting_human",
            "phase_feedback": {"content": []},
            "phase_feedback_history": {"content": [self._ENTRY]},
        })

        assert response.phase_feedback == {"content": []}
        assert response.phase_feedback_history["content"][0].note == "EN em inglês"

    def test_missing_history_is_empty(self) -> None:
        assert phase_feedback_history_field({}) == {}
        assert phase_feedback_history_field({"phase_feedback_history": []}) == {}


@pytest.mark.unit
class TestResearchRelevance:
    """Scenarios: bracketed tags are not searched; only PT/EN, on-topic hits."""

    _QUERY = "Agentes de código em times pequenos"

    def test_tags_and_emoji_are_dropped_from_the_query(self) -> None:
        topic = "[QA 2026-10-16] Agentes de código em times pequenos 🤖"
        assert search_query_for(topic) == self._QUERY

    def test_a_tag_only_topic_falls_back_to_the_topic(self) -> None:
        assert search_query_for("  [QA]  ") == "[QA]"

    def test_cyrillic_hit_is_rejected_for_language(self) -> None:
        hit = ResearchHit("QA (maksimo)", "Материал представляет собой фрагмент")
        assert hit_rejection(hit, self._QUERY) == FILTER_REASON_LANGUAGE

    def test_long_latin_hit_without_pt_or_en_words_is_rejected(self) -> None:
        snippet = "Agentes kodu w zespolach programistycznych zmieniaja przeglad kodu"
        hit = ResearchHit("Agentes kodu", snippet)
        assert hit_rejection(hit, self._QUERY) == FILTER_REASON_LANGUAGE

    def test_off_topic_english_hit_is_rejected(self) -> None:
        hit = ResearchHit("Sulfur", "Industrial sulfur demand rose this quarter.")
        assert hit_rejection(hit, self._QUERY) == FILTER_REASON_OFF_TOPIC

    def test_relevant_english_hit_is_kept(self) -> None:
        hit = ResearchHit("Coding agents", "How small teams adopt code agents.")
        assert hit_rejection(hit, self._QUERY) is None

    def test_hit_without_letters_is_judged_by_topic_only(self) -> None:
        assert hit_rejection(ResearchHit("2026", "42"), "") is None
