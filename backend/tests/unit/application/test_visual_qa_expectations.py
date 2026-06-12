"""Unit tests for visual QA expectation resolution."""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.visual_qa_expectations import (
    fallback_expectations,
    resolve_visual_qa_expectations,
)


@pytest.mark.unit
def test_fallback_expectations_use_policy_defaults() -> None:
    expectations = fallback_expectations()

    assert expectations.slide_count == 7
    assert expectations.expected_width == 2160
    assert expectations.expected_height == 2700
    assert expectations.source == "fallback"


@pytest.mark.unit
def test_resolve_visual_qa_expectations_uses_workflow_when_manifest_missing() -> None:
    expectations = resolve_visual_qa_expectations(
        workflow_payload={
            "slide_drafts": [{"heading": "One"} for _ in range(7)],
            "presentation_policy_version": "hero_lower_third_v1",
        }
    )

    assert expectations.source == "workflow"
    assert expectations.slide_count == 7
