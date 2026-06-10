"""Unit tests for deterministic carousel presentation validation."""

from __future__ import annotations

import asyncio

import pytest

from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_validation import (
    BoundedRepairRequest,
    build_validation_report,
    contains_forbidden_dash,
    contains_visible_emoji,
    run_bounded_repair,
    validate_bilingual_shape_parity,
    validate_slide_payload,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT
from rag_backend.domain.constants.carousel_presentation import (
    VALIDATION_STATUS_INVALID,
    VALIDATION_STATUS_VALID,
    VIOLATION_BODY_TOO_LONG,
    VIOLATION_COPY_TOO_MANY_LINES,
    VIOLATION_DASH_PUNCTUATION_FORBIDDEN,
    VIOLATION_HEADING_NOT_SENTENCE_CASE_EN,
    VIOLATION_ICON_NAME_NOT_ALLOWLISTED,
    VIOLATION_TRANSLATION_SHAPE_MISMATCH,
    VIOLATION_VISIBLE_EMOJI_FORBIDDEN,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1,
)
from rag_backend.domain.models.carousel_presentation import SlideValidationViolation


@pytest.fixture
def policy():
    return load_presentation_policy(PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1)


@pytest.mark.unit
class TestPresentationValidationHelpers:
    """Scenario: Deterministic validators catch policy violations."""

    def test_contains_visible_emoji_detects_decorative_emoji(self) -> None:
        assert contains_visible_emoji("Great insight ✅")
        assert not contains_visible_emoji("Plain professional copy")

    def test_contains_forbidden_dash_detects_em_and_en_dash(self) -> None:
        assert contains_forbidden_dash("One idea—another")
        assert contains_forbidden_dash("Range 10\u201320")
        assert not contains_forbidden_dash("ASCII hyphenated-token only")


@pytest.mark.unit
class TestValidateSlidePayload:
    """Gherkin: Versioned carousel presentation contract."""

    def test_rejects_visible_emoji_in_heading(self, policy) -> None:
        """WHEN visible copy contains decorative emoji THEN visible_emoji_forbidden."""
        violations = validate_slide_payload(
            {"slide_type": "content", "heading": "Key insight ✅", "body": "Detail"},
            locale=LANGUAGE_PT,
            policy=policy,
            slide_index=3,
        )
        codes = {violation.code for violation in violations}
        assert VIOLATION_VISIBLE_EMOJI_FORBIDDEN in codes

    def test_rejects_forbidden_dash_punctuation(self, policy) -> None:
        """WHEN visible copy contains em dash THEN dash_punctuation_forbidden."""
        violations = validate_slide_payload(
            {"slide_type": "content", "heading": "One idea—two", "body": "Detail"},
            locale=LANGUAGE_PT,
            policy=policy,
        )
        codes = {violation.code for violation in violations}
        assert VIOLATION_DASH_PUNCTUATION_FORBIDDEN in codes

    def test_rejects_unsupported_icon_name(self, policy) -> None:
        """WHEN structured markers use unsupported Lucide names THEN reject."""
        violations = validate_slide_payload(
            {
                "slide_type": "content",
                "heading": "Heading",
                "body": "Body",
                "features": [
                    {"icon_name": "rocket-ship", "title": "Audit", "body": "Weekly"},
                ],
            },
            locale=LANGUAGE_PT,
            policy=policy,
        )
        codes = {violation.code for violation in violations}
        assert VIOLATION_ICON_NAME_NOT_ALLOWLISTED in codes

    def test_accepts_allowlisted_icon_name(self, policy) -> None:
        violations = validate_slide_payload(
            {
                "slide_type": "content",
                "heading": "Heading",
                "body": "Body",
                "features": [
                    {"icon_name": "shield-check", "title": "Audit", "body": "Weekly"},
                ],
            },
            locale=LANGUAGE_PT,
            policy=policy,
        )
        icon_codes = {
            violation.code
            for violation in violations
            if violation.code == VIOLATION_ICON_NAME_NOT_ALLOWLISTED
        }
        assert not icon_codes

    def test_rejects_lowercase_english_heading(self, policy) -> None:
        """WHEN English headings start lowercase THEN heading_not_sentence_case_en."""
        violations = validate_slide_payload(
            {"slide_type": "content", "heading": "machine learning basics", "body": ""},
            locale=LANGUAGE_EN,
            policy=policy,
        )
        codes = {violation.code for violation in violations}
        assert VIOLATION_HEADING_NOT_SENTENCE_CASE_EN in codes

    def test_rejects_body_exceeding_max_lines_budget(self, policy) -> None:
        violations = validate_slide_payload(
            {
                "slide_type": "content",
                "heading": "Heading",
                "body": "\n".join(f"Line {line}" for line in range(1, 8)),
            },
            locale=LANGUAGE_PT,
            policy=policy,
        )
        codes = {violation.code for violation in violations}
        assert VIOLATION_COPY_TOO_MANY_LINES in codes

    def test_rejects_over_budget_body_copy(self, policy) -> None:
        violations = validate_slide_payload(
            {
                "slide_type": "content",
                "heading": "Heading",
                "body": "x" * 300,
            },
            locale=LANGUAGE_PT,
            policy=policy,
        )
        codes = {violation.code for violation in violations}
        assert VIOLATION_BODY_TOO_LONG in codes

    def test_detects_translation_shape_mismatch(self) -> None:
        """WHEN PT and EN structured shapes differ THEN translation_shape_mismatch."""
        violation = validate_bilingual_shape_parity(
            {
                "features": [
                    {"icon_name": "target", "title": "One", "body": "A"},
                    {"icon_name": "eye", "title": "Two", "body": "B"},
                ]
            },
            {
                "stats": [
                    {"value": "80%", "label": "Accuracy", "detail": "Up"},
                    {"value": "3x", "label": "Speed", "detail": "Fast"},
                    {"value": "99%", "label": "Uptime", "detail": "Stable"},
                ]
            },
            slide_index=3,
        )
        assert violation is not None
        assert violation.code == VIOLATION_TRANSLATION_SHAPE_MISMATCH


@pytest.mark.unit
class TestBoundedRepair:
    """Scenario: Invalid copy remains invalid after one repair attempt."""

    @pytest.mark.asyncio
    async def test_skips_repair_when_no_handler(self, policy) -> None:
        violations = (
            SlideValidationViolation(
                code=VIOLATION_VISIBLE_EMOJI_FORBIDDEN,
                message="emoji",
            ),
        )
        request = BoundedRepairRequest(
            locale=LANGUAGE_PT,
            payload={"slide_type": "content", "heading": "Hi ✅", "body": ""},
            violations=violations,
        )
        result = await run_bounded_repair(request, repair_fn=None, policy=policy)

        assert result.repair_attempted is False
        assert result.violations_after == violations

    @pytest.mark.asyncio
    async def test_revalidates_after_successful_repair(self, policy) -> None:
        async def _repair(
            payload: dict[str, object],
            _violations: tuple[SlideValidationViolation, ...],
            _locale: str,
        ) -> dict[str, object]:
            return {
                "slide_type": payload.get("slide_type"),
                "heading": "Clean heading",
                "body": "Clean body",
            }

        violations = (
            SlideValidationViolation(
                code=VIOLATION_VISIBLE_EMOJI_FORBIDDEN,
                message="emoji",
            ),
        )
        request = BoundedRepairRequest(
            locale=LANGUAGE_PT,
            payload={"slide_type": "content", "heading": "Hi ✅", "body": ""},
            violations=violations,
        )
        result = await run_bounded_repair(request, repair_fn=_repair, policy=policy)

        assert result.repair_attempted is True
        assert result.violations_after == ()

    @pytest.mark.asyncio
    async def test_times_out_without_second_attempt(self, policy) -> None:
        async def _slow_repair(
            _payload: dict[str, object],
            _violations: tuple[SlideValidationViolation, ...],
            _locale: str,
        ) -> dict[str, object]:
            await asyncio.sleep(0.05)
            return {"slide_type": "content", "heading": "Fixed", "body": ""}

        violations = (
            SlideValidationViolation(
                code=VIOLATION_VISIBLE_EMOJI_FORBIDDEN,
                message="emoji",
            ),
        )
        request = BoundedRepairRequest(
            locale=LANGUAGE_PT,
            payload={"slide_type": "content", "heading": "Hi ✅", "body": ""},
            violations=violations,
        )
        result = await run_bounded_repair(
            request,
            repair_fn=_slow_repair,
            timeout_seconds=0,
            policy=policy,
        )

        assert result.repair_attempted is True
        assert result.timed_out is True
        assert result.violations_after == violations


@pytest.mark.unit
class TestValidationReport:
    def test_build_validation_report_valid_when_no_violations(self) -> None:
        report = build_validation_report([])
        assert report.validation_status == VALIDATION_STATUS_VALID
        assert report.blocking is False

    def test_build_validation_report_invalid_when_violations_present(self) -> None:
        report = build_validation_report(
            [
                SlideValidationViolation(
                    code=VIOLATION_VISIBLE_EMOJI_FORBIDDEN,
                    message="emoji",
                )
            ]
        )
        assert report.validation_status == VALIDATION_STATUS_INVALID
        assert report.blocking is True
