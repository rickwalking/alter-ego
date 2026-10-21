"""One label-scaffolding detector for the drafter parser AND the gate,
plus the per-locale emphasis rule (F-03, F-04, F-09).

Gherkin: tests/features/carousel_label_scaffolding_ae0436.feature
The fixtures are the real prod strings from carousels 7acaf967 and 5344b6c6.

The PT_BR fixtures are prod payloads from the 2026-10-19 QA run (carousels 7acaf967 and
5344b6c6).
"""

from __future__ import annotations

from typing import cast

import pytest

from rag_backend.application.services.carousel.editorial_distribution_generation import (
    _build_translation_payload,
)
from rag_backend.application.services.carousel.label_scaffolding import (
    has_scaffold_labels,
    scaffold_label_details,
    strip_scaffold_labels,
)
from rag_backend.application.services.carousel.owner_autofix_text import (
    normalize_emphasis,
)
from rag_backend.application.services.carousel.presentation_copy_repair import (
    deterministic_repair_slide_payload,
)
from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
    render_presentation_policy_context,
)
from rag_backend.application.services.carousel.presentation_review_pipeline import (
    build_presentation_review_updates,
    validate_localized_slides,
)
from rag_backend.application.services.carousel.presentation_validation import (
    ValidatePayloadCommand,
    validate_slide_payload,
)
from rag_backend.domain.constants.carousel_presentation import (
    VIOLATION_DRAFTING_SCAFFOLD_PRESENT,
    VIOLATION_EMPHASIS_MARKUP_LOCALE_MISMATCH,
)

V4 = "hero_lower_third_v4"

PT_BR_BODY = "**PT-BR**\nInovação não exige **bilhões**\nA pressão competitiva não é mais sobre escala, é sobre **eficiência**."
CTA_CREATOR_BODY = (
    "Then save this carousel and send it to whoever is locking in the AI stack. "
    "**CTA creator: radar IA.**"
)
PT_COLON_HEADING = "PT: Heading: A versão para robótica"
PT_STAR_STAR = "**PT** ** **"
SLIDE_5_EN_BODY = "DeepSeek cuts **cost per token** for the same work."
SLIDE_1_PT_BODY = "O modelo usa <strong>eficiência</strong> desde a base."


def _policy():
    return load_presentation_policy(V4)


def _codes(payload: dict[str, object], locale: str) -> set[str]:
    violations = validate_slide_payload(
        ValidatePayloadCommand(payload, locale=locale, policy=_policy())
    )
    return {violation.code for violation in violations}


def _fields(payload: dict[str, object], locale: str) -> set[tuple[str | None, str]]:
    violations = validate_slide_payload(
        ValidatePayloadCommand(payload, locale=locale, policy=_policy())
    )
    return {(violation.field, violation.code) for violation in violations}


def _blockers(payload: dict[str, object], locale: str) -> set[tuple[str | None, str]]:
    violations = validate_slide_payload(
        ValidatePayloadCommand(payload, locale=locale, policy=_policy())
    )
    return {
        (violation.field, violation.code)
        for violation in violations
        if violation.is_blocker
    }


@pytest.mark.unit
class TestLabelScaffoldingDetector:
    """Scenarios: locale markers and field labels are detected at their positions.

    Mid-sentence plain labels are real copy, and bold emphasis without a label colon is
    plain copy.
    """

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("**PT-BR**", "PT-BR"),
            ("**PT**", "PT"),
            ("**EN:**", "EN"),
            ("**EN-US**", "EN-US"),
            ("**pt_br:**", "pt_br"),
            ("PT-BR: Inovação", "PT-BR"),
            ("PT: Heading: A versão", "PT"),
            ("PT", "PT"),
            ("en", "en"),
            ("**PT** ** **", "PT"),
            ("**PT-BR** Inovação não exige", "PT-BR"),
        ],
    )
    def test_locale_markers_in_every_variant(self, text: str, expected: str) -> None:
        """Scenario: Locale markers in every variant are detected at their positions."""
        details = scaffold_label_details(text)
        assert expected in details

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("**Heading:** A versão", "Heading"),
            ("**Body:** A versão", "Body"),
            ("**CTA creator: radar IA.**", "CTA creator"),
            ("**CTA: call now**", "CTA"),
            ("**Summary:** Três pontos", "Summary"),
            ("**TL;DR: a fronteira**", "TL;DR"),
            ("SLIDE 3: the twist", "SLIDE 3"),
            ("TITLE: A versão", "TITLE"),
            ("KEY POINTS: um, dois", "KEY POINTS"),
            ("Intro **Heading:** here", "Heading"),
        ],
    )
    def test_field_labels_in_every_variant(self, text: str, expected: str) -> None:
        """Scenario: Field labels are detected at their scaffold positions."""
        details = scaffold_label_details(text)
        assert expected in details

    def test_clean_copy_has_no_labels(self) -> None:
        clean = "Inovação não exige bilhões: a pressão é sobre eficiência."
        assert not has_scaffold_labels(clean)
        assert scaffold_label_details(clean) == ()

    @pytest.mark.parametrize(
        "text",
        [
            "Mande o body: JSON com o prompt e o modelo.",
            "Leia o title: da issue antes.",
            "The response body: a JSON array.",
            "TL;DR: o custo caiu 3x.",
            "the **Summary** of the changes is short",
        ],
    )
    def test_mid_sentence_plain_labels_are_not_scaffolding(self, text: str) -> None:
        """Scenario: A mid-sentence plain label is real copy, not scaffolding."""
        assert not has_scaffold_labels(text)
        assert strip_scaffold_labels(text) == text


@pytest.mark.unit
class TestDrafterStrip:
    """Scenarios: the drafter parser strips the prod leaks at the source."""

    def test_prod_pt_br_body_is_stripped(self) -> None:
        """Scenario: The drafter strip removes PT-BR markers."""
        assert strip_scaffold_labels(PT_BR_BODY).startswith(
            "Inovação não exige **bilhões**"
        )
        assert "PT-BR" not in strip_scaffold_labels(PT_BR_BODY)

    def test_pt_star_star_and_pt_heading_garbage(self) -> None:
        """Scenario: PT ** ** and PT: Heading: leave no marker behind."""
        assert strip_scaffold_labels(PT_STAR_STAR) == ""
        assert strip_scaffold_labels(PT_COLON_HEADING) == "A versão para robótica"

    def test_cta_creator_label_is_unwrapped(self) -> None:
        """Scenario: a bold CTA creator phrase keeps its value, not the label."""
        assert strip_scaffold_labels(CTA_CREATOR_BODY) == (
            "Then save this carousel and send it to whoever is locking in the AI stack. "
            "radar IA."
        )

    def test_ae0430_strip_behavior_is_kept(self) -> None:
        """The earlier bold-marker strip keeps working (regression)."""
        assert strip_scaffold_labels("**PT**\n**body:** Texto.\n**EN:**") == "Texto."

    def test_bold_pt_br_draft_builds_a_clean_pt_payload(self) -> None:
        """Scenario: A bold PT-BR draft builds a clean PT payload."""
        draft: dict[str, object] = {
            "slide_index": 5,
            "slide_type": "content",
            "title": "Inovação não exige bilhões",
            "draft_text": "**PT-BR**\n**body:** Inovação não exige bilhões.",
        }
        review = build_presentation_review_updates([draft], policy_version=V4)
        slides = cast(list[dict[str, object]], review["localized_slides"])
        pt = cast(dict[str, object], slides[0]["presentation_pt"])
        assert "PT-BR" not in str(pt["body"])
        assert str(pt["body"]).startswith("Inovação não exige bilhões.")

    @pytest.mark.parametrize(
        "text",
        [
            PT_BR_BODY,
            CTA_CREATOR_BODY,
            PT_COLON_HEADING,
            PT_STAR_STAR,
            "**PT**\n**body:** Texto.\n**EN:**",
            "**PT-BR** Inovação não exige **bilhões**",
            "SLIDE 3: the twist",
            "Intro **Heading:** here",
            "**CTA: call now**",
        ],
    )
    def test_every_flagged_text_is_deterministically_strippable(
        self, text: str
    ) -> None:
        """Scenario: Everything the detector flags is deterministically strippable.

        Invariant (orchestrator review): a blocking violation can never be one
        the deterministic repair cannot clear, so a flagged text must stop
        being flagged after ``strip_scaffold_labels`` runs.
        """
        assert has_scaffold_labels(text)
        assert not has_scaffold_labels(strip_scaffold_labels(text))


@pytest.mark.unit
class TestGateFlagsLeaks:
    """Scenarios: the content gate flags the prod leaks as blockers."""

    def _content(self, locale: str, body: str) -> dict[str, object]:
        heading = (
            "A pressão é eficiência" if locale == "pt" else "The pressure is efficiency"
        )
        return {"slide_type": "content", "heading": heading, "body": body}

    def test_pt_br_marker_is_a_blocker_on_the_body(self) -> None:
        """Scenario: The content gate flags the prod leaks as blockers."""
        payload = self._content("pt", PT_BR_BODY)
        assert ("body", VIOLATION_DRAFTING_SCAFFOLD_PRESENT) in _blockers(payload, "pt")

    def test_cta_creator_label_is_a_blocker_on_the_en_body(self) -> None:
        payload = self._content("en", CTA_CREATOR_BODY)
        assert ("body", VIOLATION_DRAFTING_SCAFFOLD_PRESENT) in _blockers(payload, "en")

    def test_pt_heading_garbage_is_a_blocker(self) -> None:
        payload = self._content("pt", "A pressão é eficiência.")
        payload["heading"] = PT_COLON_HEADING
        assert ("heading", VIOLATION_DRAFTING_SCAFFOLD_PRESENT) in _blockers(
            payload, "pt"
        )

    def test_feature_body_is_label_checked(self) -> None:
        """Scenario: Item texts are label-checked and stripped too."""
        payload: dict[str, object] = {
            "slide_type": "content",
            "heading": "A pressão é eficiência",
            "body": "Inovação não exige bilhões: é sobre eficiência.",
            "content_kind": "features",
            "features": [
                {"title": "Custo", "body": "**Body:** o custo por token cai."},
            ],
        }
        fields = _fields(payload, "pt")
        assert ("features[0].body", VIOLATION_DRAFTING_SCAFFOLD_PRESENT) in fields

    def test_the_deterministic_repair_clears_the_leaks(self) -> None:
        """Scenario: The deterministic repair strips the labels and the gate turns green."""
        payload = self._content("pt", PT_BR_BODY)
        violations = validate_slide_payload(
            ValidatePayloadCommand(payload, locale="pt", policy=_policy())
        )
        repaired = deterministic_repair_slide_payload(payload, tuple(violations), "pt")
        assert VIOLATION_DRAFTING_SCAFFOLD_PRESENT not in _codes(repaired, "pt")

        en_payload = self._content("en", CTA_CREATOR_BODY)
        violations = validate_slide_payload(
            ValidatePayloadCommand(en_payload, locale="en", policy=_policy())
        )
        repaired = deterministic_repair_slide_payload(
            en_payload, tuple(violations), "en"
        )
        assert VIOLATION_DRAFTING_SCAFFOLD_PRESENT not in _codes(repaired, "en")
        assert "CTA creator" not in str(repaired.get("body"))

    def test_the_repair_strips_item_labels(self) -> None:
        payload: dict[str, object] = {
            "slide_type": "content",
            "heading": "A pressão é eficiência",
            "body": "Inovação não exige bilhões: é sobre eficiência.",
            "content_kind": "features",
            "features": [
                {"title": "Custo", "body": "**Body:** o custo por token cai."},
            ],
        }
        violations = validate_slide_payload(
            ValidatePayloadCommand(payload, locale="pt", policy=_policy())
        )
        repaired = deterministic_repair_slide_payload(payload, tuple(violations), "pt")
        features = cast(list[dict[str, object]], repaired["features"])
        assert features[0]["body"] == "o custo por token cai."
        assert VIOLATION_DRAFTING_SCAFFOLD_PRESENT not in _codes(repaired, "pt")


@pytest.mark.unit
class TestEmphasisLocale:
    """Scenarios: EN ** normalizes to <strong>; a mismatch is a blocker."""

    def test_en_double_stars_normalize_to_strong(self) -> None:
        """Scenario: EN ** emphasis normalizes to <strong> at write time."""
        assert normalize_emphasis("en", SLIDE_5_EN_BODY) == (
            "DeepSeek cuts <strong>cost per token</strong> for the same work."
        )

    def test_pt_strong_normalizes_to_double_stars(self) -> None:
        """Scenario: PT <strong> emphasis normalizes to ** at write time."""
        assert normalize_emphasis("pt", SLIDE_1_PT_BODY) == (
            "O modelo usa **eficiência** desde a base."
        )

    def test_empty_pairs_are_left_alone(self) -> None:
        assert normalize_emphasis("en", "Keep ** ** as is") == "Keep ** ** as is"
        assert normalize_emphasis("pt", "Keep <strong> </strong> as is") == (
            "Keep <strong> </strong> as is"
        )

    def test_en_double_stars_are_a_blocker(self) -> None:
        """Scenario: A surviving emphasis mismatch is a blocker."""
        payload = {
            "slide_type": "content",
            "heading": "The pressure is efficiency",
            "body": SLIDE_5_EN_BODY,
        }
        assert (
            "body",
            VIOLATION_EMPHASIS_MARKUP_LOCALE_MISMATCH,
        ) in _blockers(payload, "en")

    def test_pt_strong_tags_are_a_blocker(self) -> None:
        payload = {
            "slide_type": "content",
            "heading": "A pressão é eficiência",
            "body": SLIDE_1_PT_BODY,
        }
        assert (
            "body",
            VIOLATION_EMPHASIS_MARKUP_LOCALE_MISMATCH,
        ) in _blockers(payload, "pt")

    def test_the_deterministic_repair_clears_the_mismatch(self) -> None:
        payload = {
            "slide_type": "content",
            "heading": "The pressure is efficiency",
            "body": SLIDE_5_EN_BODY,
        }
        violations = validate_slide_payload(
            ValidatePayloadCommand(payload, locale="en", policy=_policy())
        )
        repaired = deterministic_repair_slide_payload(payload, tuple(violations), "en")
        assert repaired["body"] == (
            "DeepSeek cuts <strong>cost per token</strong> for the same work."
        )
        assert VIOLATION_EMPHASIS_MARKUP_LOCALE_MISMATCH not in _codes(repaired, "en")

    def test_conforming_emphasis_is_not_flagged(self) -> None:
        pt_payload = {
            "slide_type": "content",
            "heading": "A pressão é eficiência",
            "body": "Inovação não exige **bilhões**.",
        }
        en_payload = {
            "slide_type": "content",
            "heading": "The pressure is efficiency",
            "body": "Innovation does not require <strong>billions</strong>.",
        }
        assert VIOLATION_EMPHASIS_MARKUP_LOCALE_MISMATCH not in _codes(pt_payload, "pt")
        assert VIOLATION_EMPHASIS_MARKUP_LOCALE_MISMATCH not in _codes(en_payload, "en")

    def test_v3_policy_does_not_enforce_the_convention(self) -> None:
        """Older contracts keep their semantics (no new rule)."""
        payload = {
            "slide_type": "content",
            "heading": "The pressure is efficiency",
            "body": SLIDE_5_EN_BODY,
        }
        violations = validate_slide_payload(
            ValidatePayloadCommand(
                payload,
                locale="en",
                policy=load_presentation_policy("hero_lower_third_v3"),
            )
        )
        assert VIOLATION_EMPHASIS_MARKUP_LOCALE_MISMATCH not in {
            v.code for v in violations
        }


@pytest.mark.unit
class TestTranslationPayload:
    """Scenarios: the translation request sends PT emphasis as <strong>."""

    def test_pt_emphasis_travels_as_strong(self) -> None:
        draft: dict[str, object] = {
            "slide_index": 5,
            "title": "Inovação não exige bilhões",
            "draft_text": "A pressão é sobre **eficiência**.",
        }
        payload = _build_translation_payload([draft])
        assert payload[0]["body"] == "A pressão é sobre <strong>eficiência</strong>."

    def test_item_texts_travel_as_strong(self) -> None:
        draft: dict[str, object] = {
            "slide_index": 6,
            "title": "Salvar",
            "draft_text": "Salve o carrossel.",
            "actions": [
                {"title": "Escolha uma tarefa", "body": "Um comando **claro**."},
            ],
        }
        payload = _build_translation_payload([draft])
        actions = cast(list[dict[str, object]], payload[0]["actions"])
        assert actions[0]["body"] == "Um comando <strong>claro</strong>."

    def test_long_form_notes_are_never_rewritten(self) -> None:
        draft: dict[str, object] = {
            "slide_index": 5,
            "title": "Inovação não exige bilhões",
            "draft_text": "A pressão é sobre **eficiência**.",
            "long_form_notes": "A pressão é sobre **eficiência** e escala.",
        }
        payload = _build_translation_payload([draft])
        assert payload[0]["long_form_notes"] == (
            "A pressão é sobre **eficiência** e escala."
        )


@pytest.mark.unit
class TestPolicyContext:
    """Scenarios: the policy context never exposes schema field names."""

    def test_no_snake_case_budget_names_in_the_context(self) -> None:
        """Scenario: The policy context never exposes schema field names."""
        context = render_presentation_policy_context(_policy())
        for raw_name in (
            "cta_creator_name",
            "cta_handle",
            "cta_website",
            "closing_action_title",
            "summary_point_title",
            "feature_body",
            "intro_heading",
        ):
            assert raw_name not in context
        assert "owner name on the CTA card" in context
        assert "never visible copy" in context

    def test_v4_rule_summaries_name_the_labels(self) -> None:
        policy = _policy()
        summaries = [rule.summary for rule in policy.visible_text.rules]
        scaffold = next(s for s in summaries if "drafting" in s.lower())
        assert "PT-BR" in scaffold and "CTA creator" in scaffold


@pytest.mark.unit
class TestFullDeckValidation:
    """Scenario: the prod leaks block the localized-slide validation."""

    def test_prod_leaks_block_and_repair_clears(self) -> None:
        """The generation-time bounded repair clears both payloads."""
        slide: dict[str, object] = {
            "slide_index": 5,
            "slide_type": "content",
            "presentation_pt": {
                "slide_type": "content",
                "heading": "Inovação não exige bilhões",
                "body": PT_BR_BODY,
            },
            "presentation_en": {
                "slide_type": "content",
                "heading": "Innovation does not require billions",
                "body": CTA_CREATOR_BODY,
            },
        }
        report = validate_localized_slides([slide], policy_version=V4)
        blocked = {
            (v.field, v.code, v.locale)
            for v in report.violations
            if v.code == VIOLATION_DRAFTING_SCAFFOLD_PRESENT
        }
        assert ("body", VIOLATION_DRAFTING_SCAFFOLD_PRESENT, "pt") in blocked
        assert ("body", VIOLATION_DRAFTING_SCAFFOLD_PRESENT, "en") in blocked

        from rag_backend.application.services.carousel.presentation_review_repair import (
            repair_localized_slides_sync,
        )

        repaired = repair_localized_slides_sync([slide], policy_version=V4)
        report_after = validate_localized_slides(repaired, policy_version=V4)
        assert VIOLATION_DRAFTING_SCAFFOLD_PRESENT not in {
            v.code for v in report_after.violations
        }
