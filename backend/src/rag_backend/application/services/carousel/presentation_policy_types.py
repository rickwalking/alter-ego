"""Typed dataclasses for the versioned carousel presentation policy."""

from __future__ import annotations

from dataclasses import dataclass, field

from rag_backend.domain.constants.carousel_presentation import (
    DEFAULT_VIOLATION_SEVERITY,
    SEVERITY_WARNING,
)


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
class CasingRulePolicy:
    """A PT casing rule with per-slide-type exemptions (AE-0312)."""

    code: str
    exempt_slide_types: frozenset[str] = frozenset()

    def applies_to(self, slide_type: str) -> bool:
        """Return True when this casing rule is not exempted for the slide type."""
        return slide_type not in self.exempt_slide_types


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
    # AE-0312 severity + casing metadata. v1 policies parse these as empty, so
    # every violation defaults to blocker and no casing rules fire.
    rule_severities: dict[str, str] = field(default_factory=dict)
    casing_rules: tuple[CasingRulePolicy, ...] = ()
    proper_nouns: tuple[str, ...] = ()

    @property
    def has_casing_rules(self) -> bool:
        """Return True when this policy defines PT casing rules (v2+)."""
        return bool(self.casing_rules)

    def severity_for(self, code: str) -> str:
        """Resolve a violation code's severity, defaulting to blocker."""
        return self.rule_severities.get(code, DEFAULT_VIOLATION_SEVERITY)

    def casing_rule(self, code: str) -> CasingRulePolicy | None:
        """Return the casing rule for a code, or None when not defined."""
        for rule in self.casing_rules:
            if rule.code == code:
                return rule
        return None

    def is_casing_warning(self, code: str) -> bool:
        """Return True when a code is a warning-severity casing rule."""
        return self.severity_for(code) == SEVERITY_WARNING


class PresentationPolicyError(LookupError):
    """Raised when a presentation policy cannot be loaded or parsed."""


__all__ = [
    "CarouselPresentationPolicy",
    "CasingRulePolicy",
    "FontPolicy",
    "GeometryBudget",
    "PresentationPolicyError",
    "SlideTypePolicy",
    "TextBudget",
    "VisibleTextPolicy",
    "VisibleTextRule",
]
