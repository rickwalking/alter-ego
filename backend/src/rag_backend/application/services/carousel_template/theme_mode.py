"""Light/dark surface tokens for slide text composition.

The slide artwork is theme-coloured by the image strategy, but the overlaid
text + scrim must adapt to the palette's *background* luminance: a light
palette needs dark ink and a light scrim, a dark palette needs white ink and a
dark scrim. This module computes the mode from the background colour (WCAG
relative luminance) and returns the ``:root`` CSS variable values the slide CSS
consumes. Dark palettes get the exact legacy values (byte-identical output).
"""

from __future__ import annotations

from collections.abc import Mapping

# Backgrounds at/above this relative luminance are treated as light. Dark
# palettes sit near 0.0-0.02; light/editorial palettes near 0.9+.
LIGHT_BACKGROUND_LUMINANCE_THRESHOLD = 0.5

_THEME_BACKGROUND_KEY = "background"
_SRGB_LINEAR_THRESHOLD = 0.03928
_HEX_RGB_LENGTH = 6

# Dark mode = the historical hardcoded values (keeps dark output identical).
_DARK_SURFACE_VARS: dict[str, str] = {
    "text": "#ffffff",
    "text_60": "rgba(255,255,255,0.63)",
    "text_55": "rgba(255,255,255,0.55)",
    "text_48": "rgba(255,255,255,0.48)",
    "text_06": "rgba(255,255,255,0.06)",
    "scrim_0": "rgba(10,12,20,0.08)",
    "scrim_25": "rgba(10,12,20,0.35)",
    "scrim_50": "rgba(10,12,20,0.75)",
    "card_bg_1": "rgba(6,10,18,0.88)",
    "card_bg_2": "rgba(6,10,18,0.64)",
    "item_bg": "rgba(10,12,20,0.8)",
    "body_bg": "#060a12",
    "body_text": "rgba(255,255,255,0.85)",
}

# Light mode = dark ink + light scrim. Ink opacities are tuned so body copy
# clears WCAG AA (>= 4.5:1) over a near-white editorial background.
_LIGHT_SURFACE_VARS: dict[str, str] = {
    "text": "#16181d",
    "text_60": "rgba(22,24,29,0.82)",
    "text_55": "rgba(22,24,29,0.74)",
    "text_48": "rgba(22,24,29,0.62)",
    "text_06": "rgba(22,24,29,0.10)",
    "scrim_0": "rgba(248,246,240,0.05)",
    "scrim_25": "rgba(248,246,240,0.45)",
    "scrim_50": "rgba(248,246,240,0.82)",
    "card_bg_1": "rgba(255,255,255,0.92)",
    "card_bg_2": "rgba(255,255,255,0.78)",
    "item_bg": "rgba(255,255,255,0.85)",
    "body_bg": "#ece9e1",
    "body_text": "rgba(22,24,29,0.85)",
}


def _srgb_channel_to_linear(channel: int) -> float:
    """Convert one 0-255 sRGB channel to linear light (WCAG)."""
    ratio = channel / 255.0
    if ratio <= _SRGB_LINEAR_THRESHOLD:
        return ratio / 12.92
    return ((ratio + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    """WCAG relative luminance of a ``#rrggbb`` colour (0.0-1.0)."""
    value = hex_color.lstrip("#")
    if len(value) != _HEX_RGB_LENGTH:
        return 0.0
    red = _srgb_channel_to_linear(int(value[0:2], 16))
    green = _srgb_channel_to_linear(int(value[2:4], 16))
    blue = _srgb_channel_to_linear(int(value[4:6], 16))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def is_light_background(background: str) -> bool:
    """True when *background* is light enough to require dark ink text."""
    return relative_luminance(background) >= LIGHT_BACKGROUND_LUMINANCE_THRESHOLD


def surface_css_vars(theme: Mapping[str, str]) -> dict[str, str]:
    """Resolve the light/dark ``:root`` surface tokens for *theme*.

    Keys: ``text``, ``text_60``, ``text_55``, ``text_48``, ``text_06``,
    ``scrim_0``, ``scrim_25``, ``scrim_50``, ``card_bg_1``, ``card_bg_2``,
    ``body_bg``, ``body_text``. A dark palette returns the legacy values.
    """
    background = theme.get(_THEME_BACKGROUND_KEY, "")
    if background and is_light_background(background):
        return dict(_LIGHT_SURFACE_VARS)
    return dict(_DARK_SURFACE_VARS)
