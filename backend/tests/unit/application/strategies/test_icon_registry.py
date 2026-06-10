"""Unit tests for Lucide icon registry.

Gherkin: tests/features/carousel_slide_layout_strategies.feature
Scenario: Structured icons are rendered as controlled Lucide SVG
"""

import pytest

from rag_backend.application.services.carousel_template.icon_registry import (
    UnknownLucideIconError,
    render_lucide_icon,
    render_structured_item_icon,
)
from rag_backend.domain.constants.carousel_presentation import LUCIDE_ICON_ALLOWLIST


@pytest.mark.unit
class TestIconRegistry:
    """Scenario: Structured icons render as controlled Lucide inline SVG."""

    @pytest.mark.parametrize("icon_name", sorted(LUCIDE_ICON_ALLOWLIST))
    def test_renders_allowlisted_icon_as_inline_svg(self, icon_name: str) -> None:
        result = render_lucide_icon(icon_name)
        assert result.startswith('<svg viewBox="0 0 24 24"')
        assert 'stroke="currentColor"' in result
        assert 'aria-hidden="true"' in result
        assert result.endswith("</svg>")

    def test_rejects_unknown_icon_name(self) -> None:
        with pytest.raises(UnknownLucideIconError, match="Lucide allowlist"):
            render_lucide_icon("rocket-ship")

    def test_rejects_legacy_emoji_icon(self) -> None:
        with pytest.raises(UnknownLucideIconError, match="Lucide allowlist"):
            render_structured_item_icon({"icon": "⚡", "title": "Fast", "body": "Speed"})

    def test_prefers_icon_name_over_legacy_icon(self) -> None:
        result = render_structured_item_icon(
            {
                "icon_name": "target",
                "icon": "⚡",
                "title": "Focus",
                "body": "Precision",
            }
        )
        assert "<circle" in result
        assert "⚡" not in result

    def test_returns_empty_string_when_icon_missing(self) -> None:
        assert render_structured_item_icon({"title": "No icon", "body": "Body"}) == ""
