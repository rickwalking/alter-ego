"""Unit tests for editorial workflow route sanitization (AE-0289).

Edited localized slides are FINAL published copy: sanitization must strip
injection-prone chars but PRESERVE case, so proper-cased headings survive and
pass ``heading_not_sentence_case_en`` validation on approve.
"""

from __future__ import annotations

from typing import cast

import pytest

from rag_backend.api.routes.carousels.editorial_workflow_routes_sanitize import (
    sanitize_structured_feedback,
)
from rag_backend.api.schemas.carousel_workflow import (
    EditorialStructuredFeedback,
    LocalizedSlideReview,
)


@pytest.mark.unit
class TestSanitizeEditedSlidesPreservesCase:
    def test_edited_slide_headings_and_bodies_keep_case(self) -> None:
        feedback = EditorialStructuredFeedback(
            edited_localized_slides=[
                LocalizedSlideReview(
                    slide_index=3,
                    slide_type="content",
                    presentation_pt={
                        "heading": "Modelos de IA e a disputa",
                        "body": "A China alcançou a fronteira com o GLM 5.2.",
                    },
                    presentation_en={
                        "heading": "AI models and the race for control",
                        "body": "China reached the frontier with GLM 5.2.",
                    },
                )
            ]
        )

        sanitized = sanitize_structured_feedback(feedback)
        assert sanitized is not None
        edited = cast(list[dict[str, object]], sanitized["edited_localized_slides"])
        slide = cast(dict[str, dict[str, str]], edited[0])

        assert slide["presentation_en"]["heading"] == (
            "AI models and the race for control"
        )
        assert slide["presentation_pt"]["heading"] == "Modelos de IA e a disputa"
        assert "GLM 5.2" in slide["presentation_en"]["body"]
