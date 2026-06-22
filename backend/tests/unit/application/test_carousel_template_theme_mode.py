"""Unit tests for light/dark slide surface tokens.

Gherkin: tests/features/carousel_design_refinement.feature
(Scenario: light palettes render dark ink text with a light scrim).

AE-0265: a light-background palette must compose dark ink text + a light scrim
so body copy clears WCAG AA; dark palettes keep their exact legacy values.
"""

import pytest

from rag_backend.application.services.carousel_template.css.base import (
    _get_neon_base_css,
)
from rag_backend.application.services.carousel_template.theme_mode import (
    is_light_background,
    relative_luminance,
    surface_css_vars,
)

_DARK = {"primary": "#ef4444", "accent": "#00d4ff", "background": "#0a0e17"}
_LIGHT = {"primary": "#111827", "accent": "#2563eb", "background": "#f7f5f0"}
_LIGHT_BACKGROUNDS = ("#fbf7f0", "#f7f5f0", "#f0fdfa")  # riso, paper, mint


def _parse_rgba(value: str) -> tuple[int, int, int, float]:
    inner = value[value.index("(") + 1 : value.index(")")]
    parts = [p.strip() for p in inner.split(",")]
    return int(parts[0]), int(parts[1]), int(parts[2]), float(parts[3])


def _blend_over(fg_rgba: str, bg_hex: str) -> str:
    r, g, b, a = _parse_rgba(fg_rgba)
    bg = bg_hex.lstrip("#")
    br, bg_, bb = int(bg[0:2], 16), int(bg[2:4], 16), int(bg[4:6], 16)
    out = (
        round(r * a + br * (1 - a)),
        round(g * a + bg_ * (1 - a)),
        round(b * a + bb * (1 - a)),
    )
    return "#{:02x}{:02x}{:02x}".format(*out)


def _contrast(hex_a: str, hex_b: str) -> float:
    la, lb = relative_luminance(hex_a), relative_luminance(hex_b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.unit
class TestThemeMode:
    def test_dark_background_is_not_light(self) -> None:
        assert is_light_background(_DARK["background"]) is False

    def test_light_backgrounds_are_light(self) -> None:
        assert all(is_light_background(b) for b in _LIGHT_BACKGROUNDS)

    def test_dark_surface_keeps_legacy_values(self) -> None:
        v = surface_css_vars(_DARK)
        assert v["text"] == "#ffffff"
        assert v["scrim_0"] == "rgba(10,12,20,0.08)"
        assert v["item_bg"] == "rgba(10,12,20,0.8)"
        assert v["body_bg"] == "#060a12"

    def test_light_surface_flips_to_dark_ink(self) -> None:
        v = surface_css_vars(_LIGHT)
        assert v["text"] == "#16181d"
        assert v["scrim_50"].startswith("rgba(248,246,240")
        assert v["item_bg"].startswith("rgba(255,255,255")


@pytest.mark.unit
class TestBodyContrast:
    def test_light_body_text_clears_wcag_aa(self) -> None:
        # Body copy uses --text-60; it must clear 4.5:1 on every light palette.
        text_60 = surface_css_vars(_LIGHT)["text_60"]
        for bg in _LIGHT_BACKGROUNDS:
            effective = _blend_over(text_60, bg)
            assert _contrast(effective, bg) >= 4.5, (bg, effective)


@pytest.mark.unit
class TestBaseCss:
    def test_dark_css_unchanged(self) -> None:
        css = _get_neon_base_css(_DARK)
        assert "--text: #ffffff;" in css
        assert "rgba(10,12,20,0.08)" in css  # scrim value still present via var

    def test_light_css_has_dark_ink_and_no_white_root_text(self) -> None:
        css = _get_neon_base_css(_LIGHT)
        root = css.split("--font-mono")[0]
        assert "--text: #16181d;" in css
        assert "#ffffff" not in root
