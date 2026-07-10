"""Unit tests for carousel presentation policy loading."""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.presentation_policy import (
    PresentationPolicyError,
    _assert_casing_rules_have_severity,
    _parse_casing,
    _parse_rule_severities,
    load_presentation_policy,
    render_presentation_policy_context,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    CasingRulePolicy,
)
from rag_backend.domain.constants.carousel_presentation import (
    SEVERITY_WARNING,
    VIOLATION_HEADING_NOT_SENTENCE_CASE_PT,
    VIOLATION_PROPER_NOUN_CASING,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1,
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2,
)


@pytest.mark.unit
class TestPresentationPolicy:
    """Gherkin: Versioned carousel presentation contract."""

    def test_load_hero_lower_third_v1_exposes_slide_contract(self) -> None:
        """WHEN hero_lower_third_v1 loads THEN slide count and types are available."""
        policy = load_presentation_policy(
            PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1
        )

        assert policy.version == PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1
        assert policy.slide_count == 7
        assert tuple(slide.slide_type for slide in policy.slides) == (
            "intro",
            "summary",
            "content",
            "content",
            "content",
            "closing",
            "cta",
        )
        assert policy.artwork_slides == (1, 2, 3, 4, 5, 6)
        assert policy.cta_avatar_required is True

    def test_load_hero_lower_third_v1_exposes_copy_budgets(self) -> None:
        """WHEN hero_lower_third_v1 loads THEN copy budgets are typed."""
        policy = load_presentation_policy(
            PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1
        )

        assert policy.copy_budgets["intro_heading"].max_characters == 72
        assert policy.copy_budgets["intro_heading"].max_lines == 3
        assert policy.copy_budgets["content_body"].max_characters == 220
        assert policy.copy_budgets["feature_title"].max_characters == 32

    def test_load_hero_lower_third_v1_exposes_visible_text_rules(self) -> None:
        """WHEN hero_lower_third_v1 loads THEN visible-text rule IDs are exposed."""
        policy = load_presentation_policy(
            PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1
        )

        rule_ids = {rule.rule_id for rule in policy.visible_text.rules}
        assert "visible_emoji_forbidden" in rule_ids
        assert "lucide_icon_name_required" in rule_ids
        assert "dash_punctuation_forbidden" in rule_ids

    def test_load_hero_lower_third_v1_exposes_geometry_and_icons(self) -> None:
        """WHEN hero_lower_third_v1 loads THEN geometry ratios and icons are exposed."""
        policy = load_presentation_policy(
            PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1
        )

        intro = policy.slides[0]
        assert intro.copy_start_ratio == 0.55
        assert policy.geometry.viewport_standard_width == 1080
        assert policy.geometry.viewport_standard_height == 1350
        assert policy.lucide_icon_allowlist == (
            "chart-column",
            "book-open",
            "newspaper",
            "brain",
            "target",
            "eye",
            "message-circle",
            "shield-check",
            "wrench",
            "flask-conical",
        )
        assert policy.checksum.startswith("sha256-")

    def test_render_presentation_policy_context_includes_canonical_values(self) -> None:
        """WHEN prompt context renders THEN policy version and allowlist remain aligned."""
        policy = load_presentation_policy(
            PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1
        )
        context = render_presentation_policy_context(policy)

        assert PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1 in context
        assert "Slide count: 7" in context
        assert "chart-column" in context
        assert "copy_start_ratio=0.55" in context
        assert "visible_emoji_forbidden" in context

    def test_load_v2_exposes_casing_rules_and_severities(self) -> None:
        """AE-0312: v2 carries PT casing rules, proper nouns, and severities."""
        policy = load_presentation_policy(
            PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2
        )

        assert policy.has_casing_rules is True
        assert policy.proper_nouns == ("Claude", "Anthropic")
        assert policy.severity_for(VIOLATION_HEADING_NOT_SENTENCE_CASE_PT) == (
            SEVERITY_WARNING
        )
        assert policy.is_casing_warning(VIOLATION_PROPER_NOUN_CASING) is True

    def test_loader_rejects_v2_casing_rule_without_severity(self) -> None:
        """Rule-fires (AE-0180): a casing rule with no severity fails the load."""
        casing_rules = (CasingRulePolicy(code="heading_not_sentence_case_pt"),)

        with pytest.raises(PresentationPolicyError):
            _assert_casing_rules_have_severity(casing_rules, {})

    def test_loader_rejects_invalid_severity_value(self) -> None:
        """Rule-fires (AE-0180): an invalid severity value fails the load."""
        with pytest.raises(PresentationPolicyError):
            _parse_rule_severities({"heading_empty": "not_a_severity"})

    def test_parse_casing_reads_exempt_slide_types(self) -> None:
        rules, proper_nouns = _parse_casing({
            "proper_nouns": ["Claude"],
            "rules": [
                {"code": "heading_not_sentence_case_pt", "exempt_slide_types": ["cta"]}
            ],
        })

        assert proper_nouns == ("Claude",)
        assert rules[0].exempt_slide_types == frozenset({"cta"})

    def test_unknown_policy_version_falls_back_to_v1(self) -> None:
        """AE-0312 rollback safety: an unknown version falls back to v1, never raises.

        Scenario: a code rollback after the in-flight upgrade migration cannot
        freeze v2-stamped rows (see carousel_pt_casing_severity.feature).
        """
        policy = load_presentation_policy("unknown_policy_v9")

        assert policy.version == PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1
        assert policy.has_casing_rules is False
