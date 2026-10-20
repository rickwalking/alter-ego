"""AE-0439 (QA F-13): the SSE review gate payload maps image_assets container
paths to owner preview URLs.

Gherkin: tests/features/blog_carousel_minors_ae0439.feature
  - Scenario: The workflow state maps image_assets to owner preview URLs
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.editorial_workflow_sse_build import (
    build_review_gate_payload,
)
from rag_backend.application.services.carousel.workflow_state import (
    CarouselWorkflowState,
)

PROJECT_ID = "7acaf967-0124-44db-8636-0589906b3c33"


def _state(image_assets: object) -> CarouselWorkflowState:
    state: CarouselWorkflowState = {
        "project_id": PROJECT_ID,
        "current_phase": "images",
        "phase_status": "awaiting_human",
        "image_assets": image_assets,
    }
    return state


@pytest.mark.unit
class TestReviewGateImageAssets:
    def test_container_paths_become_preview_urls(self) -> None:
        payload = build_review_gate_payload(
            _state(
                [
                    f"/app/output/carousels/{PROJECT_ID}/images/slide_1.jpg",
                    f"/app/output/carousels/{PROJECT_ID}/images/slide_3.jpg",
                ]
            )
        )
        assert payload["image_assets"] == [
            f"/api/carousels/{PROJECT_ID}/preview/images/slide_1.jpg",
            f"/api/carousels/{PROJECT_ID}/preview/images/slide_3.jpg",
        ]

    def test_existing_urls_pass_through(self) -> None:
        payload = build_review_gate_payload(
            _state(
                [
                    "https://example.com/cover.jpg",
                    f"/api/carousels/{PROJECT_ID}/preview/images/slide_1.jpg",
                ]
            )
        )
        assert payload["image_assets"] == [
            "https://example.com/cover.jpg",
            f"/api/carousels/{PROJECT_ID}/preview/images/slide_1.jpg",
        ]

    def test_no_assets_stays_empty(self) -> None:
        assert build_review_gate_payload(_state(None))["image_assets"] == []
