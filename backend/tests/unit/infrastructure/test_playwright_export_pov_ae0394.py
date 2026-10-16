"""POV export-canvas rules (AE-0394).

Gherkin: tests/features/carousel_pov_layouts.feature
("POV slides scale for the export canvas", "Slide 1 shows the owner's photo full-bleed").
"""

from __future__ import annotations

import re

import pytest

from rag_backend.application.services.carousel_template.css.slide_styles_pov import (
    get_pov_slide_css,
)
from rag_backend.infrastructure.external.playwright_export_pov import (
    pov_export_css,
    pov_export_injection,
)

_POV_CLASSES = (
    ".pov-presentation",
    ".pov-statement-heading",
    ".pov-statement-body",
    ".pov-hook-heading",
    ".pov-hook-sub",
    ".pov-check-item",
    ".pov-check-icon",
    ".pov-cta-sentence",
    ".pov-footer",
)


def _rule(css: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert match is not None, selector
    return match.group(1)


@pytest.mark.unit
class TestPovExportRules:
    # Scenario: POV slides scale for the export canvas
    def test_standard_canvas_sizes(self) -> None:
        css = pov_export_css(hd=False)
        assert "font-size: 84px" in _rule(css, ".pov-statement-heading")
        assert "font-size: 36px" in _rule(css, ".pov-statement-body")
        assert "font-size: 92px" in _rule(css, ".pov-hook-heading")

    def test_hd_doubles_every_size(self) -> None:
        css = pov_export_css(hd=True)
        assert "font-size: 168px" in _rule(css, ".pov-statement-heading")
        assert "font-size: 72px" in _rule(css, ".pov-statement-body")
        assert "font-size: 184px" in _rule(css, ".pov-hook-heading")
        assert "flex: 0 0 104px" in _rule(css, ".pov-check-icon")

    def test_every_pov_class_is_scaled(self) -> None:
        css = pov_export_css(hd=False)
        for selector in _POV_CLASSES:
            assert "!important" in _rule(css, selector), selector

    # Scenario: The exporter applies the POV rules
    def test_injection_appends_a_named_style(self) -> None:
        js = pov_export_injection(hd=False)
        assert "s.id = 'playwright-export-pov'" in js
        assert "document.head.appendChild(s)" in js
        assert ".pov-statement-heading" in js

    def test_injection_wraps_css_in_a_template_literal(self) -> None:
        js = pov_export_injection(hd=True)
        literal = js.split("s.textContent = ", 1)[1].split(";document", 1)[0]
        assert literal.startswith("`") and literal.endswith("`")
        assert "`" not in literal[1:-1]


@pytest.mark.unit
class TestHookPhotoFullBleed:
    # Scenario: Slide 1 shows the owner's photo full-bleed
    def test_photo_fills_the_slide(self) -> None:
        css = get_pov_slide_css({})
        box = _rule(css, ".pov-hook-photo")
        assert "inset: 0" in box
        assert "width: 100%" in box and "height: 100%" in box
        img = _rule(css, ".pov-hook-photo img")
        assert "object-fit: cover" in img
        assert "max-width: none" in img

    def test_scrim_fades_the_top_into_the_background(self) -> None:
        css = get_pov_slide_css({})
        scrim = _rule(css, ".pov-hook-photo::after")
        assert "linear-gradient" in scrim
        assert "var(--bg)" in scrim
