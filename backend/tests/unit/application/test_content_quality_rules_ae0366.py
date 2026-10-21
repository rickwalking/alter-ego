"""Sentence-case guards, repair, and the objective rubric validators.

Gherkin: tests/features/carousel_content_quality_ae0366.feature
"""

from __future__ import annotations

import dataclasses

import pytest

from rag_backend.application.services.carousel.presentation_casing import (
    CasingCheckCommand,
    casing_violations,
    repair_casing,
)
from rag_backend.application.services.carousel.presentation_content_rules import (
    ContentRuleCommand,
    TranslationCheckCommand,
    content_rule_violations,
    emphasis_markup_is_valid,
    translation_violations,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    build_presentation_review_updates,
)
from rag_backend.application.services.carousel.sentence_case import (
    capitalize_first_letter,
    capitalize_sentence_starts,
    has_lowercase_sentence,
    starts_lowercase,
)
from rag_backend.domain.constants.carousel import LANGUAGE_EN, LANGUAGE_PT
from rag_backend.domain.constants.carousel_presentation import (
    SEVERITY_BLOCKER,
    VIOLATION_BODY_EMPTY,
    VIOLATION_BODY_NOT_SENTENCE_CASE_EN,
    VIOLATION_BODY_NOT_SENTENCE_CASE_PT,
    VIOLATION_CLOSING_ACTIONS_MISSING,
    VIOLATION_EMPHASIS_MARKUP_INVALID,
    VIOLATION_HEADING_NOT_SENTENCE_CASE_PT,
    VIOLATION_SUMMARY_POINTS_MISSING,
    VIOLATION_TRANSLATION_NOT_ENGLISH,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1,
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2,
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V3,
)
from tests.unit.application.content_quality_fixtures_ae0366 import (
    FIXED_BODY_6,
    FIXED_HEADING_5,
    LOWERCASE_BODY_6,
    LOWERCASE_HEADING_5,
    clean_drafts,
    prod_drafts,
)

_V3 = PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V3


def _v3() -> CarouselPresentationPolicy:
    return load_presentation_policy(_V3)


def _v1() -> CarouselPresentationPolicy:
    return load_presentation_policy(PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1)


def _casing_codes(payload: dict[str, object], locale: str = LANGUAGE_PT) -> set[str]:
    command = CasingCheckCommand(payload=payload, locale=locale, policy=_v3())
    return {violation.code for violation in casing_violations(command)}


def _rule_codes(payload: dict[str, object], locale: str = LANGUAGE_PT) -> set[str]:
    command = ContentRuleCommand(payload=payload, locale=locale, policy=_v3())
    return {violation.code for violation in content_rule_violations(command)}


@pytest.mark.unit
class TestSentenceCaseHelpers:
    """Scenario: the repair capitalizes only the first letter, locale-safe."""

    def test_capitalizes_prod_heading(self) -> None:
        assert capitalize_first_letter(LOWERCASE_HEADING_5) == FIXED_HEADING_5

    def test_capitalizes_accented_first_letter(self) -> None:
        assert capitalize_first_letter("à frente do time") == "À frente do time"
        assert capitalize_first_letter("época dourada") == "Época dourada"

    def test_capitalizes_every_sentence_start(self) -> None:
        assert capitalize_sentence_starts(LOWERCASE_BODY_6) == FIXED_BODY_6

    def test_skips_markup_and_quotes(self) -> None:
        assert capitalize_first_letter("<strong>o</strong> modelo") == (
            "<strong>O</strong> modelo"
        )
        assert capitalize_first_letter('"argon" chegou') == '"Argon" chegou'
        assert capitalize_first_letter("**novo** modelo") == "**Novo** modelo"

    def test_leading_digit_is_sentence_case(self) -> None:
        assert starts_lowercase("5 coisas que mudam") is False
        assert capitalize_first_letter("5 coisas que mudam") == "5 coisas que mudam"

    def test_allowlisted_lowercase_brand_is_kept(self) -> None:
        allowlist = ("iPhone", "eBay")
        assert starts_lowercase("iPhone 17 chegou", allowlist) is False
        assert capitalize_first_letter("iPhone 17 chegou", allowlist) == (
            "iPhone 17 chegou"
        )
        assert starts_lowercase("iphoneiro novo", allowlist) is True

    def test_non_one_to_one_uppercase_is_left_alone(self) -> None:
        assert capitalize_first_letter("ßtraße") == "ßtraße"

    def test_repair_is_idempotent_and_empty_safe(self) -> None:
        assert capitalize_sentence_starts(FIXED_BODY_6) == FIXED_BODY_6
        assert capitalize_sentence_starts("") == ""
        assert capitalize_first_letter("...") == "..."
        assert has_lowercase_sentence("Tudo certo. Nada errado.") is False
        assert has_lowercase_sentence("Tudo certo. nada errado.") is True


@pytest.mark.unit
class TestSentenceCaseRulesBlock:
    """Scenario: lowercase headline/body text is a blocking violation."""

    def test_lowercase_pt_heading_blocks(self) -> None:
        payload = {"slide_type": "content", "heading": LOWERCASE_HEADING_5}
        command = CasingCheckCommand(payload=payload, locale=LANGUAGE_PT, policy=_v3())

        violations = casing_violations(command)

        assert {v.code for v in violations} == {VIOLATION_HEADING_NOT_SENTENCE_CASE_PT}
        assert all(v.severity == SEVERITY_BLOCKER for v in violations)

    def test_fully_lowercase_closing_flags_heading_body_and_items(self) -> None:
        payload = {
            "slide_type": "closing",
            "heading": "o que muda para devs",
            "body": "à frente, o time testa.",
            "actions": [{"title": "teste a api", "body": "rode seus prompts."}],
        }
        command = CasingCheckCommand(payload=payload, locale=LANGUAGE_PT, policy=_v3())

        fields = {v.field for v in casing_violations(command)}

        assert fields == {
            "heading",
            "body",
            "actions[0].title",
            "actions[0].body",
        }

    def test_en_body_and_item_titles_block(self) -> None:
        payload = {
            "slide_type": "content",
            "heading": "Fine heading",
            "body": "it shares the lead.",
            "features": [{"title": "better reasoning", "body": "Solves tasks."}],
        }

        assert _casing_codes(payload, LANGUAGE_EN) == {
            VIOLATION_BODY_NOT_SENTENCE_CASE_EN,
            "heading_not_sentence_case_en",
        }

    def test_exempt_slide_type_is_respected(self) -> None:
        policy = _v3()
        exempt = tuple(
            dataclasses.replace(rule, exempt_slide_types=frozenset({"content"}))
            if rule.code == VIOLATION_HEADING_NOT_SENTENCE_CASE_PT
            else rule
            for rule in policy.casing_rules
        )
        relaxed = dataclasses.replace(policy, casing_rules=exempt)
        payload = {"slide_type": "content", "heading": LOWERCASE_HEADING_5}

        command = CasingCheckCommand(
            payload=payload, locale=LANGUAGE_PT, policy=relaxed
        )

        assert casing_violations(command) == []
        assert repair_casing(payload, LANGUAGE_PT, relaxed)["heading"] == (
            LOWERCASE_HEADING_5
        )

    def test_intentional_lowercase_allowlist_is_respected(self) -> None:
        payload = {"slide_type": "content", "heading": "iPhone 17 chega ao Brasil"}

        assert _casing_codes(payload) == set()
        assert repair_casing(payload, LANGUAGE_PT, _v3())["heading"] == (
            "iPhone 17 chega ao Brasil"
        )

    def test_v1_policy_has_no_casing_rules(self) -> None:
        payload = {"slide_type": "content", "heading": LOWERCASE_HEADING_5}
        command = CasingCheckCommand(payload=payload, locale=LANGUAGE_PT, policy=_v1())

        assert casing_violations(command) == []
        assert repair_casing(payload, LANGUAGE_PT, _v1()) == payload

    def test_repair_canonicalizes_configured_proper_nouns_in_items(self) -> None:
        payload = {
            "slide_type": "closing",
            "heading": "o que muda no brasil",
            "actions": [{"title": "teste", "body": "rode no argon. depois compare."}],
        }

        repaired = repair_casing(payload, LANGUAGE_PT, _v3())

        assert repaired["heading"] == "O que muda no Brasil"
        assert repaired["actions"] == [
            {"title": "Teste", "body": "Rode no Argon. Depois compare."}
        ]


@pytest.mark.unit
class TestStructureRules:
    """Scenario: empty slides and missing items are blocking violations."""

    def test_content_without_body_or_features_is_empty(self) -> None:
        payload = {"slide_type": "content", "heading": "Título", "body": ""}

        assert _rule_codes(payload) == {VIOLATION_BODY_EMPTY}

    def test_content_with_three_complete_features_needs_no_body(self) -> None:
        features = [{"title": f"Item {n}", "body": "Corpo."} for n in range(3)]
        payload = {"slide_type": "content", "heading": "T", "features": features}

        assert _rule_codes(payload) == set()

    def test_intro_without_body_is_empty(self) -> None:
        assert _rule_codes({"slide_type": "intro", "heading": "T"}) == {
            VIOLATION_BODY_EMPTY
        }

    def test_closing_needs_three_complete_actions(self) -> None:
        actions = [{"title": "A", "body": "B."}, {"title": "C", "body": ""}]
        payload = {"slide_type": "closing", "heading": "T", "actions": actions}

        assert _rule_codes(payload) == {VIOLATION_CLOSING_ACTIONS_MISSING}

    def test_closing_without_anything_is_empty_and_missing_actions(self) -> None:
        assert _rule_codes({"slide_type": "closing", "heading": "T"}) == {
            VIOLATION_BODY_EMPTY,
            VIOLATION_CLOSING_ACTIONS_MISSING,
        }

    def test_summary_needs_three_complete_points(self) -> None:
        points = [{"title": "A", "body": "B."}]
        payload = {"slide_type": "summary", "heading": "T", "summary_points": points}

        assert _rule_codes(payload) == {VIOLATION_SUMMARY_POINTS_MISSING}

    def test_cta_is_exempt(self) -> None:
        assert _rule_codes({"slide_type": "cta", "heading": "Salve"}) == set()

    def test_v1_policy_has_no_structure_rules(self) -> None:
        command = ContentRuleCommand(
            payload={"slide_type": "content", "heading": "T"},
            locale=LANGUAGE_PT,
            policy=_v1(),
        )

        assert content_rule_violations(command) == []


@pytest.mark.unit
class TestEmphasisMarkup:
    """Scenario: emphasis uses balanced <strong> tags only."""

    @pytest.mark.parametrize(
        "text",
        [
            "Texto com <strong>ênfase</strong> e <strong>outra</strong>.",
            "Sem marcação nenhuma.",
            "Com **markdown** permitido.",
        ],
    )
    def test_valid_markup(self, text: str) -> None:
        assert emphasis_markup_is_valid(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "most resilient against strongindirect injections/strong.",
            "<em>itálico</em>",
            "<strong>aberto sem fechar",
            "fechado</strong> sem abrir",
            "<strong>um <strong>dois</strong></strong>",
        ],
    )
    def test_invalid_markup(self, text: str) -> None:
        assert emphasis_markup_is_valid(text) is False

    def test_mangled_tags_block_in_items(self) -> None:
        payload = {
            "slide_type": "content",
            "heading": "T",
            "body": "Corpo <b>errado</b>.",
        }

        command = ContentRuleCommand(payload=payload, locale=LANGUAGE_EN, policy=_v3())
        violations = content_rule_violations(command)

        assert [v.code for v in violations] == [VIOLATION_EMPHASIS_MARKUP_INVALID]
        assert violations[0].field == "body"


@pytest.mark.unit
class TestTranslationIsEnglish:
    """Scenario: PT copy pasted into the EN fields blocks."""

    def test_identical_body_blocks(self) -> None:
        command = TranslationCheckCommand(
            pt_payload={"heading": "Argon", "body": "O corpo em português."},
            en_payload={
                "heading": "Argon",
                "body": "o corpo em <strong>português</strong>.",
            },
            policy=_v3(),
            slide_index=3,
        )

        violations = translation_violations(command)

        assert [(v.code, v.field) for v in violations] == [
            (VIOLATION_TRANSLATION_NOT_ENGLISH, "body")
        ]

    def test_translated_copy_passes(self) -> None:
        command = TranslationCheckCommand(
            pt_payload={"heading": "Um título curto", "body": "O corpo em português."},
            en_payload={"heading": "A short title", "body": "The body in English."},
            policy=_v3(),
        )

        assert translation_violations(command) == []

    def test_v1_policy_skips_the_check(self) -> None:
        payload = {"heading": "Um título curto e igual", "body": ""}
        command = TranslationCheckCommand(
            pt_payload=payload, en_payload=payload, policy=_v1()
        )

        assert translation_violations(command) == []


@pytest.mark.unit
class TestProdShapedDrafts:
    """Scenario: the prod carousel 8e350d6e drafts are blocked, clean ones pass."""

    def _report(self, drafts: list[dict[str, object]]) -> dict[str, object]:
        updates = build_presentation_review_updates(drafts, policy_version=_V3)
        report = updates["presentation_validation"]
        assert isinstance(report, dict)
        return report

    def test_prod_drafts_block_on_empty_body_and_lowercase(self) -> None:
        report = self._report(prod_drafts())

        assert report["blocking"] is True
        found = {
            (violation["slide_index"], violation["code"])
            for violation in report["violations"]
        }
        assert (4, VIOLATION_BODY_EMPTY) in found
        assert (5, VIOLATION_HEADING_NOT_SENTENCE_CASE_PT) in found
        assert (6, VIOLATION_HEADING_NOT_SENTENCE_CASE_PT) in found
        assert (6, VIOLATION_BODY_NOT_SENTENCE_CASE_PT) in found

    def test_clean_drafts_pass(self) -> None:
        report = self._report(clean_drafts())

        assert report["blocking"] is False
        assert report["violations"] == []

    def test_repaired_copy_is_capitalized_without_guessing_nouns(self) -> None:
        """ "gemini" is not a configured proper noun, so it is not guessed."""
        updates = build_presentation_review_updates(prod_drafts(), policy_version=_V3)
        slides = updates["localized_slides"]
        assert isinstance(slides, list)

        slide5_pt = slides[4]["presentation_pt"]
        slide6_pt = slides[5]["presentation_pt"]

        assert slide5_pt["heading"] == FIXED_HEADING_5
        assert slide6_pt["heading"] == "O que muda para devs no Brasil"
        assert slide6_pt["body"] == FIXED_BODY_6


@pytest.mark.unit
class TestV2StaysFrozen:
    """Scenario: a v2 project keeps its frozen (warning-only) casing semantics."""

    def test_v2_prod_drafts_do_not_gain_v3_blockers(self) -> None:
        updates = build_presentation_review_updates(
            prod_drafts(),
            policy_version=PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2,
        )
        report = updates["presentation_validation"]
        assert isinstance(report, dict)
        codes = {violation["code"] for violation in report["violations"]}

        assert VIOLATION_BODY_EMPTY not in codes
        assert "casing_repairs" not in updates["localized_slides"][4]
        assert all(v["severity"] != SEVERITY_BLOCKER for v in report["violations"])
