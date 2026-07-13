"""Unit tests for PT sentence-case validation and casing repair (AE-0312).

Gherkin: tests/features/carousel_pt_casing_severity.feature
"""

from __future__ import annotations

import dataclasses

import pytest

from rag_backend.application.services.carousel.presentation_casing import (
    CasingCheckCommand,
    canonicalize_proper_nouns,
    casing_violations,
    repair_casing,
    uppercase_sentence_starts,
)
from rag_backend.application.services.carousel.presentation_policy import (
    CasingRulePolicy,
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT
from rag_backend.domain.constants.carousel_presentation import (
    SEVERITY_WARNING,
    VIOLATION_BODY_NOT_SENTENCE_CASE_PT,
    VIOLATION_HEADING_NOT_SENTENCE_CASE_PT,
    VIOLATION_PROPER_NOUN_CASING,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1,
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2,
)

# Real prod payloads from incident 66014ba3 (2026-07-10).
INCIDENT_HEADING_1 = "o **espaço mental** privado descoberto no claude"
INCIDENT_HEADING_1_FIXED = "O **espaço mental** privado descoberto no Claude"
INCIDENT_HEADING_2 = "o que os pesquisadores **descobriram**"
INCIDENT_HEADING_2_FIXED = "O que os pesquisadores **descobriram**"
INCIDENT_BODY = (
    "antes de emitir uma única palavra, o modelo constrói algo. "
    "uma janela inesperada para a arquitetura do pensamento artificial."
)
INCIDENT_BODY_FIXED = (
    "Antes de emitir uma única palavra, o modelo constrói algo. "
    "Uma janela inesperada para a arquitetura do pensamento artificial."
)


def _v2() -> CarouselPresentationPolicy:
    return load_presentation_policy(PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2)


def _v1() -> CarouselPresentationPolicy:
    return load_presentation_policy(PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1)


def _codes(command: CasingCheckCommand) -> set[str]:
    return {violation.code for violation in casing_violations(command)}


@pytest.mark.unit
class TestCasingValidation:
    """Scenario: Lowercase PT heading is flagged and repaired."""

    def test_lowercase_pt_heading_and_proper_noun_are_flagged(self) -> None:
        command = CasingCheckCommand(
            payload={"slide_type": "intro", "heading": INCIDENT_HEADING_1, "body": ""},
            locale=LANGUAGE_PT,
            policy=_v2(),
            slide_index=1,
        )

        assert _codes(command) == {
            VIOLATION_HEADING_NOT_SENTENCE_CASE_PT,
            VIOLATION_PROPER_NOUN_CASING,
        }

    def test_casing_violations_are_warning_severity(self) -> None:
        command = CasingCheckCommand(
            payload={
                "slide_type": "content",
                "heading": INCIDENT_HEADING_2,
                "body": "",
            },
            locale=LANGUAGE_PT,
            policy=_v2(),
            slide_index=2,
        )

        violations = casing_violations(command)
        assert violations
        assert all(v.severity == SEVERITY_WARNING for v in violations)

    def test_lowercase_body_sentence_start_is_flagged(self) -> None:
        command = CasingCheckCommand(
            payload={
                "slide_type": "content",
                "heading": "Título",
                "body": INCIDENT_BODY,
            },
            locale=LANGUAGE_PT,
            policy=_v2(),
            slide_index=3,
        )

        assert VIOLATION_BODY_NOT_SENTENCE_CASE_PT in _codes(command)

    def test_lowercase_claude_flagged_in_english_locale(self) -> None:
        """proper_noun_casing applies to both locales."""
        command = CasingCheckCommand(
            payload={"slide_type": "intro", "heading": "The claude window", "body": ""},
            locale=LANGUAGE_EN,
            policy=_v2(),
            slide_index=1,
        )

        assert _codes(command) == {VIOLATION_PROPER_NOUN_CASING}

    def test_correct_casing_produces_no_violations(self) -> None:
        command = CasingCheckCommand(
            payload={
                "slide_type": "intro",
                "heading": INCIDENT_HEADING_1_FIXED,
                "body": INCIDENT_BODY_FIXED,
            },
            locale=LANGUAGE_PT,
            policy=_v2(),
            slide_index=1,
        )

        assert casing_violations(command) == []

    def test_accented_first_letter_is_handled(self) -> None:
        command = CasingCheckCommand(
            payload={"slide_type": "content", "heading": "época dourada", "body": ""},
            locale=LANGUAGE_PT,
            policy=_v2(),
            slide_index=1,
        )

        assert VIOLATION_HEADING_NOT_SENTENCE_CASE_PT in _codes(command)

    def test_v1_policy_reports_no_casing_violations(self) -> None:
        command = CasingCheckCommand(
            payload={"slide_type": "intro", "heading": INCIDENT_HEADING_1, "body": ""},
            locale=LANGUAGE_PT,
            policy=_v1(),
            slide_index=1,
        )

        assert casing_violations(command) == []

    def test_exempted_slide_type_keeps_stylistic_lowercase(self) -> None:
        """Scenario: Exempted slide type keeps stylistic lowercase."""
        base = _v2()
        exempt_rules = tuple(
            CasingRulePolicy(code=rule.code, exempt_slide_types=frozenset({"cta"}))
            for rule in base.casing_rules
        )
        policy = dataclasses.replace(base, casing_rules=exempt_rules)
        command = CasingCheckCommand(
            payload={"slide_type": "cta", "heading": "call to action", "body": ""},
            locale=LANGUAGE_PT,
            policy=policy,
            slide_index=7,
        )

        assert casing_violations(command) == []


@pytest.mark.unit
class TestCasingRepair:
    """Scenario: deterministic casing repair fixes the incident payloads."""

    def test_incident_heading_1_is_repaired(self) -> None:
        repaired = repair_casing(
            {"slide_type": "intro", "heading": INCIDENT_HEADING_1, "body": ""},
            LANGUAGE_PT,
            _v2(),
        )

        assert repaired["heading"] == INCIDENT_HEADING_1_FIXED

    def test_incident_heading_2_is_repaired(self) -> None:
        repaired = repair_casing(
            {"slide_type": "content", "heading": INCIDENT_HEADING_2, "body": ""},
            LANGUAGE_PT,
            _v2(),
        )

        assert repaired["heading"] == INCIDENT_HEADING_2_FIXED

    def test_body_sentence_starts_repaired_preserving_markdown(self) -> None:
        """Scenario: Body sentence starts are repaired without touching markdown."""
        body = "antes de **emitir** uma palavra. uma janela **inesperada** surge."
        repaired = repair_casing(
            {"slide_type": "content", "heading": "Título", "body": body},
            LANGUAGE_PT,
            _v2(),
        )

        assert repaired["body"] == (
            "Antes de **emitir** uma palavra. Uma janela **inesperada** surge."
        )

    def test_repair_is_idempotent(self) -> None:
        once = repair_casing(
            {
                "slide_type": "intro",
                "heading": INCIDENT_HEADING_1,
                "body": INCIDENT_BODY,
            },
            LANGUAGE_PT,
            _v2(),
        )
        twice = repair_casing(once, LANGUAGE_PT, _v2())

        assert once == twice

    def test_repaired_payload_revalidates_clean(self) -> None:
        repaired = repair_casing(
            {
                "slide_type": "intro",
                "heading": INCIDENT_HEADING_1,
                "body": INCIDENT_BODY,
            },
            LANGUAGE_PT,
            _v2(),
        )
        command = CasingCheckCommand(
            payload=repaired, locale=LANGUAGE_PT, policy=_v2(), slide_index=1
        )

        assert casing_violations(command) == []

    def test_v1_policy_applies_no_casing_mutation(self) -> None:
        payload = {"slide_type": "intro", "heading": INCIDENT_HEADING_1, "body": ""}
        repaired = repair_casing(payload, LANGUAGE_PT, _v1())

        assert repaired["heading"] == INCIDENT_HEADING_1


@pytest.mark.unit
class TestCasingHelpers:
    """Direct coverage of the deterministic string transforms."""

    def test_uppercase_sentence_starts_preserves_markdown(self) -> None:
        assert uppercase_sentence_starts("**palavra** aqui. outra frase.") == (
            "**Palavra** aqui. Outra frase."
        )

    def test_canonicalize_proper_nouns_rewrites_casing(self) -> None:
        assert (
            canonicalize_proper_nouns("claude e ANTHROPIC", ("Claude", "Anthropic"))
            == "Claude e Anthropic"
        )

    def test_canonicalize_proper_nouns_ignores_substrings(self) -> None:
        assert canonicalize_proper_nouns("claudette", ("Claude",)) == "claudette"
