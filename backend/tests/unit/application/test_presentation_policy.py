"""Unit tests for carousel presentation policy loading."""

from __future__ import annotations

import pytest

from rag_backend.application.services.carousel.presentation_policy import (
    PresentationPolicyError,
    load_presentation_policy,
    render_presentation_policy_context,
)
from rag_backend.domain.constants.presentation_policy import (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1,
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

    def test_unknown_policy_version_raises(self) -> None:
        """WHEN an unknown policy version loads THEN loader fails."""
        with pytest.raises(PresentationPolicyError):
            load_presentation_policy("unknown_policy_v9")
