"""WCAG AA contrast checks and repair for generated palettes.

The slide ink is the template's (``theme_mode``): dark ink on a light
background, white on a dark one. A background whose ink fails AA is mixed
towards black (white ink then passes once the luminance drops under ~0.18); a
light background always passes with the dark ink. A colour that fails against
the background is mixed towards black on a light background and towards white
on a dark one. Both walks end at a colour that passes (black on a light
background is at least 11:1, white on a repaired dark one at least 4.5:1), so a
repaired palette always meets AA.
"""

from __future__ import annotations

from rag_backend.application.services.carousel_template.theme_mode import (
    is_light_background,
    relative_luminance,
)
from rag_backend.domain.constants.palette_generation import (
    CONTRAST_REPAIR_STEP,
    MIX_TARGET_BLACK,
    MIX_TARGET_WHITE,
    SLIDE_INK_ON_DARK,
    SLIDE_INK_ON_LIGHT,
    WCAG_AA_TEXT_CONTRAST,
)

_LUMINANCE_OFFSET = 0.05
_HEX_PREFIX = "#"
_CHANNEL_MAX = 255


def contrast_ratio(first: str, second: str) -> float:
    """WCAG contrast ratio of two ``#rrggbb`` colours (1.0-21.0)."""
    lighter, darker = sorted(
        (relative_luminance(first), relative_luminance(second)), reverse=True
    )
    return (lighter + _LUMINANCE_OFFSET) / (darker + _LUMINANCE_OFFSET)


def slide_ink(background: str) -> str:
    """The text colour the slide template puts on ``background``."""
    return SLIDE_INK_ON_LIGHT if is_light_background(background) else SLIDE_INK_ON_DARK


def _channels(colour: str) -> tuple[int, int, int]:
    value = colour.lstrip(_HEX_PREFIX)
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _mix(colour: str, target: str, amount: float) -> str:
    pairs = zip(_channels(colour), _channels(target), strict=True)
    mixed = (min(_CHANNEL_MAX, round(c + (t - c) * amount)) for c, t in pairs)
    return _HEX_PREFIX + "".join(f"{channel:02x}" for channel in mixed)


def _walk_until(colour: str, target: str, against: str | None) -> str:
    """Mix ``colour`` towards ``target`` until it reaches AA against ``against``.

    ``against=None`` checks ``colour`` against its own slide ink. When no partial
    mix passes, the target itself is the answer.
    """
    for step in range(round(1 / CONTRAST_REPAIR_STEP)):
        candidate = _mix(colour, target, step * CONTRAST_REPAIR_STEP)
        other = slide_ink(candidate) if against is None else against
        if contrast_ratio(candidate, other) >= WCAG_AA_TEXT_CONTRAST:
            return candidate
    return target


def repair_background(background: str) -> str:
    """``background`` darkened just enough for its slide ink to reach AA."""
    return _walk_until(background, MIX_TARGET_BLACK, None)


def repair_against(colour: str, background: str) -> str:
    """``colour`` moved away from ``background`` until the pair reaches AA."""
    target = MIX_TARGET_BLACK if is_light_background(background) else MIX_TARGET_WHITE
    return _walk_until(colour, target, background)


__all__ = ["contrast_ratio", "repair_against", "repair_background", "slide_ink"]
