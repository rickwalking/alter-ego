"""Unit tests for presentation review state builders."""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.presentation_review import (
    build_presentation_review_updates,
    has_blocking_presentation_validation,
    resolve_presentation_review_from_state,
)
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_ICON_NAME_NOT_ALLOWLISTED,
)


@pytest.mark.unit
class TestPresentationReview:
    """Gherkin: Versioned carousel presentation contract."""

    def test_builds_localized_slides_and_validation_from_legacy_drafts(self) -> None:
        """WHEN slide drafts exist THEN localized_slides and validation are available."""
        updates = build_presentation_review_updates(
            [
                {
                    "slide_index": 1,
                    "slide_type": "intro",
                    "title": "Hook",
                    "draft_text": "Subtitle",
                }
            ],
            translations_en={
                1: {"heading": "Hook EN", "body": "Subtitle EN"},
            },
        )

        localized = updates["localized_slides"]
        assert isinstance(localized, list)
        assert len(localized) == 1
        assert localized[0]["presentation_pt"]["heading"] == "Hook"
        assert localized[0]["presentation_en"]["heading"] == "Hook EN"
        validation = updates["presentation_validation"]
        assert isinstance(validation, dict)
        assert validation["blocking"] is False

    def test_flags_blocking_violations_for_invalid_copy(self) -> None:
        """WHEN visible copy violates a blocking rule THEN approval is blocked."""
        updates = build_presentation_review_updates([
            {
                "slide_index": 3,
                "slide_type": "content",
                "title": "Key insight",
                "draft_text": "Detail",
                "features": [
                    {
                        "icon_name": "rocket-ship",
                        "title": "Audit",
                        "body": "Weekly",
                    }
                ],
            }
        ])
        validation = updates["presentation_validation"]
        assert validation["blocking"] is True
        codes = {item["code"] for item in validation["violations"]}
        assert VIOLATION_ICON_NAME_NOT_ALLOWLISTED in codes
        assert has_blocking_presentation_validation(updates) is True

    def test_resolves_review_fields_from_slide_drafts_when_missing(self) -> None:
        """WHEN workflow state lacks review fields THEN they are derived on read."""
        resolved = resolve_presentation_review_from_state({
            "slide_drafts": [
                {
                    "slide_index": 1,
                    "slide_type": "intro",
                    "title": "Hook",
                    "draft_text": "Subtitle",
                }
            ]
        })
        assert len(resolved["localized_slides"]) == 1
        assert "presentation_validation" in resolved
