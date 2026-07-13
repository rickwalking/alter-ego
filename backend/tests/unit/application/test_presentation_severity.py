"""Severity-aware blocking decision tests (AE-0312).

Gherkin: tests/features/carousel_pt_casing_severity.feature
"""

from __future__ import annotations

from typing import cast

import pytest

from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_review import (
    has_blocking_presentation_validation,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    WORKFLOW_STATE_LOCALIZED_SLIDES_KEY,
    WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY,
    validate_localized_slides,
)
from rag_backend.application.services.carousel.presentation_validation import (
    build_validation_report,
)
from rag_backend.domain.constants.carousel_presentation import (
    SEVERITY_BLOCKER,
    SEVERITY_WARNING,
    VIOLATION_HEADING_EMPTY,
    VIOLATION_HEADING_NOT_SENTENCE_CASE_PT,
    VIOLATION_VISIBLE_EMOJI_FORBIDDEN,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2,
)
from rag_backend.domain.models.carousel_presentation import (
    SlideValidationViolation,
    ViolationSeverity,
)


def _violation(code: str, severity: str) -> SlideValidationViolation:
    # cast at the typed fixture boundary: severity is a validated Literal value.
    return SlideValidationViolation(
        code=code,
        message=f"seeded {code}",
        slide_index=1,
        severity=cast(ViolationSeverity, severity),
    )


def _v2_slide(heading: str, body: str = "Corpo válido.") -> dict[str, object]:
    payload = {"slide_type": "intro", "heading": heading, "body": body}
    return {
        "slide_index": 1,
        "slide_type": "intro",
        "presentation_pt": dict(payload),
        "presentation_en": {
            "slide_type": "intro",
            "heading": "Valid heading",
            "body": "Valid body.",
        },
    }


@pytest.mark.unit
class TestSeverityDerivedBlocking:
    """Scenario: Casing warnings never block approval."""

    def test_warning_only_report_is_not_blocking(self) -> None:
        report = build_validation_report([
            _violation(VIOLATION_HEADING_NOT_SENTENCE_CASE_PT, SEVERITY_WARNING)
        ])

        assert report.blocking is False
        assert report.validation_status == "invalid"
        assert report.violations, "warnings stay visible in the report"

    def test_blocker_report_blocks(self) -> None:
        report = build_validation_report([
            _violation(VIOLATION_HEADING_EMPTY, SEVERITY_BLOCKER)
        ])

        assert report.blocking is True

    def test_warning_plus_blocker_blocks_on_the_blocker(self) -> None:
        report = build_validation_report([
            _violation(VIOLATION_HEADING_NOT_SENTENCE_CASE_PT, SEVERITY_WARNING),
            _violation(VIOLATION_VISIBLE_EMOJI_FORBIDDEN, SEVERITY_BLOCKER),
        ])

        assert report.blocking is True

    def test_absent_severity_defaults_to_blocker(self) -> None:
        report = build_validation_report([
            SlideValidationViolation(code=VIOLATION_HEADING_EMPTY, message="x")
        ])

        assert report.blocking is True


@pytest.mark.unit
class TestPerRuleBlockingSweep:
    """Absent-severity hardening: pre-existing rules still block.

    Enumerates rule codes DYNAMICALLY from the loaded policy (single source of
    truth) so new rules are automatically covered.
    """

    def test_every_blocker_rule_blocks_and_warnings_do_not(self) -> None:
        policy = load_presentation_policy(
            PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2
        )
        assert policy.rule_severities, "v2 must declare rule severities"
        for code, severity in policy.rule_severities.items():
            report = build_validation_report([_violation(code, severity)])
            expected = severity == SEVERITY_BLOCKER
            assert report.blocking is expected, f"{code} blocking mismatch"


@pytest.mark.unit
class TestStoredReportAgreement:
    """Scenario: the stored report's blocking equals the severity decision."""

    def test_casing_only_stored_report_is_not_blocking(self) -> None:
        report = validate_localized_slides(
            [_v2_slide("heading em minúsculas no claude")],
            policy_version=PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2,
        )

        assert report.blocking is False
        codes = {violation.code for violation in report.violations}
        assert VIOLATION_HEADING_NOT_SENTENCE_CASE_PT in codes

    def test_blocker_stored_report_is_blocking(self) -> None:
        # Emoji is a blocker rule; combine with a casing warning.
        report = validate_localized_slides(
            [_v2_slide("heading no claude 🚀")],
            policy_version=PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2,
        )

        assert report.blocking is True
        codes = {violation.code for violation in report.violations}
        assert VIOLATION_VISIBLE_EMOJI_FORBIDDEN in codes
        assert VIOLATION_HEADING_NOT_SENTENCE_CASE_PT in codes


@pytest.mark.unit
class TestLocaleSeverityIntegration:
    """Cross-ticket: casing-only reports never block the workflow read paths."""

    def test_casing_only_report_lets_locale_validation_pass(self) -> None:
        report = validate_localized_slides(
            [_v2_slide("um título em minúsculas")],
            policy_version=PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2,
        )

        assert report.blocking is False
        assert all(v.severity == SEVERITY_WARNING for v in report.violations)

    def test_casing_only_state_does_not_block_approval(self) -> None:
        """Cross-ticket: AE-0309's blocking check treats casing-only as passable."""
        state = {
            WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY: (
                PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2
            ),
            WORKFLOW_STATE_LOCALIZED_SLIDES_KEY: [_v2_slide("um título em minúsculas")],
        }

        assert has_blocking_presentation_validation(state) is False

    def test_blocker_state_blocks_approval(self) -> None:
        """Cross-ticket: an unrepairable blocker (empty heading) still blocks."""
        state = {
            WORKFLOW_STATE_PRESENTATION_POLICY_VERSION_KEY: (
                PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2
            ),
            WORKFLOW_STATE_LOCALIZED_SLIDES_KEY: [_v2_slide("")],
        }

        assert has_blocking_presentation_validation(state) is True
