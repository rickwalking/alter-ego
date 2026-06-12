"""Unit tests for reviewer slide-copy edits at the content gate.

Feature: Versioned carousel presentation contract
Scenario: Reviewer edits are merged, re-validated, and propagated to drafts
Scenario: Invalid edits keep approval blocked

Feature: Null-safe draft edits (see features/carousel_null_safety.feature)
Scenario: Nullable locale values are guarded before assignment
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.presentation_review import (
    WORKFLOW_STATE_LOCALIZED_SLIDES_KEY,
    WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY,
    WORKFLOW_STATE_TRANSLATIONS_EN_KEY,
)
from rag_backend.application.services.carousel.presentation_review_edits import (
    _apply_edits_to_drafts,
    _locale_heading_body,
    _safe_str,
    apply_localized_slide_edits,
    edited_slides_block_approval,
    merge_localized_slide_edits,
)


def _slide(index: int, heading_pt: str, heading_en: str) -> dict[str, object]:
    return {
        "slide_index": index,
        "slide_type": "intro" if index == 1 else "hero_content",
        "presentation_pt": {
            "slide_type": "intro" if index == 1 else "hero_content",
            "heading": heading_pt,
            "body": f"Corpo {index}",
        },
        "presentation_en": {
            "slide_type": "intro" if index == 1 else "hero_content",
            "heading": heading_en,
            "body": f"Body {index}",
        },
    }


def _state() -> dict[str, object]:
    return {
        WORKFLOW_STATE_LOCALIZED_SLIDES_KEY: [
            _slide(1, "Titulo original", "Original title"),
            _slide(2, "Segundo slide", "Second slide"),
        ],
        "slide_drafts": [
            {
                "slide_index": 1,
                "title": "Titulo original",
                "draft_text": "Corpo 1",
            },
            {
                "slide_index": 2,
                "title": "Segundo slide",
                "draft_text": "Corpo 2",
            },
        ],
        WORKFLOW_STATE_TRANSLATIONS_EN_KEY: {
            "1": {"heading": "Original title", "body": "Body 1"},
            "2": {"heading": "Second slide", "body": "Body 2"},
        },
    }


@pytest.mark.unit
class TestMergeLocalizedSlideEdits:
    def test_merges_edit_by_slide_index(self) -> None:
        current = [_slide(1, "Antigo", "Old"), _slide(2, "Mantido", "Kept")]
        edits = [_slide(1, "Novo", "New")]

        merged = merge_localized_slide_edits(current, edits)

        pt_payload = merged[0]["presentation_pt"]
        assert isinstance(pt_payload, dict)
        assert pt_payload["heading"] == "Novo"
        kept_payload = merged[1]["presentation_pt"]
        assert isinstance(kept_payload, dict)
        assert kept_payload["heading"] == "Mantido"

    def test_ignores_edits_for_unknown_slides(self) -> None:
        current = [_slide(1, "Antigo", "Old")]
        edits = [_slide(9, "Fantasma", "Ghost")]

        merged = merge_localized_slide_edits(current, edits)

        pt_payload = merged[0]["presentation_pt"]
        assert isinstance(pt_payload, dict)
        assert pt_payload["heading"] == "Antigo"


@pytest.mark.unit
class TestApplyLocalizedSlideEdits:
    def test_edits_propagate_to_drafts_and_translations(self) -> None:
        state = _state()
        edits = [_slide(1, "Titulo editado", "Edited title")]

        updates = apply_localized_slide_edits(state, edits)

        localized = updates[WORKFLOW_STATE_LOCALIZED_SLIDES_KEY]
        assert isinstance(localized, list)
        first = localized[0]
        assert isinstance(first, dict)
        pt_payload = first["presentation_pt"]
        assert isinstance(pt_payload, dict)
        assert pt_payload["heading"] == "Titulo editado"

        drafts = updates["slide_drafts"]
        assert isinstance(drafts, list)
        first_draft = drafts[0]
        assert isinstance(first_draft, dict)
        assert first_draft["title"] == "Titulo editado"
        assert first_draft["heading"] == "Titulo editado"

        translations = updates[WORKFLOW_STATE_TRANSLATIONS_EN_KEY]
        assert isinstance(translations, dict)
        en_entry = translations["1"]
        assert isinstance(en_entry, dict)
        assert en_entry["heading"] == "Edited title"

    def test_validation_report_included(self) -> None:
        updates = apply_localized_slide_edits(
            _state(),
            [_slide(1, "Titulo editado", "Edited title")],
        )

        validation = updates[WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY]
        assert isinstance(validation, dict)
        assert "blocking" in validation
        assert "violations" in validation


@pytest.mark.unit
class TestEditedSlidesBlockApproval:
    def test_valid_edits_do_not_block(self) -> None:
        assert (
            edited_slides_block_approval(
                _state(),
                [_slide(1, "Titulo editado", "Edited title")],
            )
            is False
        )

    def test_overlong_heading_blocks_approval(self) -> None:
        oversized = "X" * 500
        assert (
            edited_slides_block_approval(
                _state(),
                [_slide(1, oversized, "Edited title")],
            )
            is True
        )


@pytest.mark.unit
class TestSafeStr:
    def test_none_returns_default(self) -> None:
        assert _safe_str(None) == ""

    def test_none_returns_custom_default(self) -> None:
        assert _safe_str(None, "fallback") == "fallback"

    def test_value_is_stringified(self) -> None:
        assert _safe_str(42) == "42"
        assert _safe_str("text") == "text"


@pytest.mark.unit
class TestLocaleHeadingBody:
    def test_none_payload_returns_empty_strings(self) -> None:
        assert _locale_heading_body(None) == ("", "")

    def test_explicit_none_values_do_not_become_literal_none(self) -> None:
        # Guard clause: a None value must not stringify to "None".
        payload: dict[str, object] = {"heading": None, "body": None}
        assert _locale_heading_body(payload) == ("", "")

    def test_present_values_are_returned(self) -> None:
        payload: dict[str, object] = {"heading": "H", "body": "B"}
        assert _locale_heading_body(payload) == ("H", "B")


@pytest.mark.unit
class TestApplyEditsToDrafts:
    def test_non_dict_drafts_are_skipped(self) -> None:
        # Guard clause: only dict drafts are processed.
        drafts: list[dict[str, object]] = [{"slide_index": 1, "title": "Keep"}]
        result = _apply_edits_to_drafts(drafts, {})
        assert result == [{"slide_index": 1, "title": "Keep"}]

    def test_missing_localized_entry_copies_draft_unchanged(self) -> None:
        # Guard clause: localized is None -> draft copied as-is.
        drafts: list[dict[str, object]] = [{"slide_index": 5, "title": "Untouched"}]
        result = _apply_edits_to_drafts(drafts, {})
        assert result[0]["title"] == "Untouched"
        assert result[0] is not drafts[0]  # defensive copy
