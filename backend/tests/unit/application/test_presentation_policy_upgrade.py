"""In-flight presentation-policy upgrade migration tests (AE-0312).

Gherkin: tests/features/carousel_pt_casing_severity.feature
"""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.presentation_policy_upgrade import (
    build_policy_downgrade_updates,
    build_policy_upgrade_updates,
    should_upgrade_project,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    WORKFLOW_STATE_LOCALIZED_SLIDES_KEY,
    WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY,
    WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY,
)
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_HEADING_NOT_SENTENCE_CASE_PT,
)
from rag_backend.domain.constants.presentation_policy import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2,
)

_LOWERCASE_HEADING = "um título em minúsculas no claude"


def _parked_v1_state() -> dict[str, object]:
    """A final_review-parked project on v1 with a lowercase PT heading."""
    return {
        "current_phase": "final_review",
        WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY: (
            DEFAULT_PRESENTATION_POLICY_VERSION
        ),
        WORKFLOW_STATE_LOCALIZED_SLIDES_KEY: [
            {
                "slide_index": 1,
                "slide_type": "intro",
                "presentation_pt": {
                    "slide_type": "intro",
                    "heading": _LOWERCASE_HEADING,
                    "body": "Corpo válido.",
                },
                "presentation_en": {
                    "slide_type": "intro",
                    "heading": "Valid heading",
                    "body": "Valid body.",
                },
            }
        ],
        WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY: {
            "validation_status": "valid",
            "validated_at": "2026-07-10T00:00:00+00:00",
            "blocking": False,
            "violations": [],
        },
    }


def _report(updates: dict[str, object]) -> dict[str, object]:
    report = updates[WORKFLOW_STATE_PRESENTATION_VALIDATION_KEY]
    assert isinstance(report, dict)
    return report


@pytest.mark.unit
class TestShouldUpgradeProject:
    def test_non_completed_v1_project_upgrades(self) -> None:
        assert should_upgrade_project("designing", "hero_lower_third_v1") is True

    def test_non_completed_null_version_upgrades(self) -> None:
        assert should_upgrade_project("drafting", None) is True

    def test_completed_project_untouched(self) -> None:
        assert should_upgrade_project("completed", "hero_lower_third_v1") is False

    def test_already_v2_is_idempotent(self) -> None:
        assert (
            should_upgrade_project(
                "designing", PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2
            )
            is False
        )


@pytest.mark.unit
class TestUpgradeRevalidates:
    """Scenario: a final_review-parked v1 project shows v2 casing warnings.

    Re-labeling alone would leave the stale v1 report served verbatim (r5).
    """

    def test_upgrade_bumps_version_and_stores_v2_report(self) -> None:
        updates = build_policy_upgrade_updates(_parked_v1_state())

        assert updates[WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY] == (
            PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2
        )
        report = _report(updates)
        codes = {violation["code"] for violation in report["violations"]}
        assert VIOLATION_HEADING_NOT_SENTENCE_CASE_PT in codes
        # Casing is warning-severity, so the fresh report does not block.
        assert report["blocking"] is False

    def test_downgrade_restores_v1_and_drops_casing_warnings(self) -> None:
        upgraded = build_policy_upgrade_updates(_parked_v1_state())
        # Feed the upgraded state back through the downgrade path.
        state = {**_parked_v1_state(), **upgraded}
        downgraded = build_policy_downgrade_updates(state)

        assert downgraded[WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY] == (
            DEFAULT_PRESENTATION_POLICY_VERSION
        )
        report = _report(downgraded)
        codes = {violation["code"] for violation in report["violations"]}
        assert VIOLATION_HEADING_NOT_SENTENCE_CASE_PT not in codes
