"""Typed dataclasses for the versioned carousel presentation policy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextBudget:
    """Character and optional line budget for a copy field."""

    max_characters: int
    max_lines: int | None = None


@dataclass(frozen=True)
class GeometryBudget:
    """Viewport and lower-third geometry thresholds."""

    viewport_standard_width: int
    viewport_standard_height: int
    viewport_hd_width: int
    viewport_hd_height: int
    footer_gap_standard: int
    footer_gap_hd: int
    tolerance_standard: int
    tolerance_hd: int
    near_limit_standard: int
    near_limit_hd: int
    selectors: dict[str, str]


@dataclass(frozen=True)
class VisibleTextRule:
    """Machine-readable visible-text rule identifier."""

    rule_id: str
    summary: str


@dataclass(frozen=True)
class VisibleTextPolicy:
    """Collection of visible-text rule identifiers."""

    rules: tuple[VisibleTextRule, ...]


@dataclass(frozen=True)
class SlideTypePolicy:
    """Per-slide presentation contract metadata."""

    slide_number: int
    slide_type: str
    image_required: bool
    copy_start_ratio: float | None
    avatar_required: bool = False


@dataclass(frozen=True)
class FontPolicy:
    """Required font families for export preflight."""

    heading_family: str
    body_family: str
    badge_family: str


@dataclass(frozen=True)
class CarouselPresentationPolicy:
    """Immutable typed presentation policy loaded from canonical YAML."""

    version: str
    slide_count: int
    slides: tuple[SlideTypePolicy, ...]
    artwork_slides: tuple[int, ...]
    cta_avatar_required: bool
    visible_text: VisibleTextPolicy
    copy_budgets: dict[str, TextBudget]
    geometry: GeometryBudget
    lucide_icon_allowlist: tuple[str, ...]
    fonts: FontPolicy
    intentional_lowercase_allowlist: tuple[str, ...]
    checksum: str


class PresentationPolicyError(LookupError):
    """Raised when a presentation policy cannot be loaded or parsed."""


__all__ = [
    "CarouselPresentationPolicy",
    "FontPolicy",
    "GeometryBudget",
    "PresentationPolicyError",
    "SlideTypePolicy",
    "TextBudget",
    "VisibleTextPolicy",
    "VisibleTextRule",
]
