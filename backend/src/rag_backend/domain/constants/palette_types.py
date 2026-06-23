"""Value objects for the carousel palette registry (AE-0266).

Leaf module (stdlib only) so the registry in ``carousel_themes`` can import
these without an import cycle through ``domain.constants`` /
``domain.models.carousel``. A palette's every property lives on one
``PaletteDescriptor`` row; the legacy lookup dicts/sets are *derived* from the
registry rather than hand-maintained in parallel.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PaletteMode(StrEnum):
    """Whether a palette's background is light or dark.

    Drives the slide scrim (light vs neon) and AUTO eligibility — a LIGHT
    palette must never be auto-assigned to a dark image strategy.
    """

    LIGHT = "light"
    DARK = "dark"


class PaletteKind(StrEnum):
    """How a palette is reached during theme resolution."""

    CATEGORY = "category"  # matched by topic-category keywords, in AUTO pool
    BRAND = "brand"  # matched by brand keywords (brand detection wins first)
    VARIANT = "variant"  # explicit-select only (new dark variants + light)


@dataclass(frozen=True)
class Palette:
    """A carousel color triple."""

    primary: str
    accent: str
    background: str

    def as_theme_dict(self) -> dict[str, str]:
        """Render the legacy ``{"primary","accent","background"}`` mapping."""
        return {
            "primary": self.primary,
            "accent": self.accent,
            "background": self.background,
        }


@dataclass(frozen=True)
class PaletteDescriptor:
    """One cohesive declaration of a palette and how it is selected.

    Brand/category keywords live here next to their colors (not in a separate
    parallel dict). ``image_style`` pairing + display labels are added in later
    AE-0266 phases.
    """

    key: str
    palette: Palette
    mode: PaletteMode
    kind: PaletteKind
    keywords: tuple[str, ...] = ()
    auto_selectable: bool = False

    def __post_init__(self) -> None:
        """Reject contradictions that previously caused real bugs."""
        if self.auto_selectable and self.mode is PaletteMode.LIGHT:
            msg = f"light palette {self.key!r} must not be AUTO-selectable"
            raise ValueError(msg)


__all__ = [
    "Palette",
    "PaletteDescriptor",
    "PaletteKind",
    "PaletteMode",
]
