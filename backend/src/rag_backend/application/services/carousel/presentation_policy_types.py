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
    """Per-slide presentation contract metadata.

    ``role`` is the narrative role (maps to ``slide_type``); ``optional`` says whether
    the slide may be dropped when the deck is shorter than the contract's longest
    sequence.
    """

    slide_number: int
    slide_type: str
    image_required: bool
    copy_start_ratio: float | None
    avatar_required: bool = False
    role: str | None = None
    optional: bool = False


@dataclass(frozen=True)
class SlideCountRange:
    """Deck size a contract accepts; fixed contracts are min = max."""

    minimum: int
    maximum: int
    default: int

    def accepts(self, count: int) -> bool:
        """True when ``count`` slides is a valid deck size."""
        return self.minimum <= count <= self.maximum


@dataclass(frozen=True)
class FontPolicy:
    """Required font families for export preflight."""

    heading_family: str
    body_family: str
    badge_family: str


@dataclass(frozen=True)
class CasingRulePolicy:
    """A PT casing rule with per-slide-type exemptions."""

    code: str
    exempt_slide_types: frozenset[str] = frozenset()

    def applies_to(self, slide_type: str) -> bool:
        """Return True when this casing rule is not exempted for the slide type."""
        return slide_type not in self.exempt_slide_types


@dataclass(frozen=True)
class QualityRubricItem:
    """One LLM quality-rubric item and the validator rules that enforce it.

    The contract's ``quality_rubric`` is the single source of truth.
    The prompt renders ``instruction``; the validator enforces ``rule_codes``.
    """

    rubric_id: str
    instruction: str
    rule_codes: tuple[str, ...]
    audiences: frozenset[str] = frozenset()


@dataclass(frozen=True)
class CarouselPresentationPolicy:
    """Immutable typed presentation policy loaded from canonical YAML.

    Severity and casing metadata parse as empty for v1 policies, so every violation
    defaults to blocker and no casing rules fire. ``quality_rubric`` is the LLM quality
    rubric (empty for v1). ``slide_count_range`` lists the accepted deck sizes; None
    means exactly ``slide_count``.
    """

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
    rule_severities: dict[str, str] = field(default_factory=dict)
    casing_rules: tuple[CasingRulePolicy, ...] = ()
    proper_nouns: tuple[str, ...] = ()
    quality_rubric: tuple[QualityRubricItem, ...] = ()
    slide_count_range: SlideCountRange | None = None

    @property
    def slide_range(self) -> SlideCountRange:
        """The accepted deck sizes (fixed contracts: ``slide_count`` only)."""
        if self.slide_count_range is not None:
            return self.slide_count_range
        return SlideCountRange(
            minimum=self.slide_count,
            maximum=self.slide_count,
            default=self.slide_count,
        )

    @property
    def has_roles(self) -> bool:
        """True when every slide of the contract declares a role."""
        return bool(self.slides) and all(slide.role for slide in self.slides)

    @property
    def has_casing_rules(self) -> bool:
        """Return True when this policy defines PT casing rules (v2+)."""
        return bool(self.casing_rules)

    @property
    def enforces_quality_rubric(self) -> bool:
        """Return True when this policy carries the LLM quality rubric (v3+)."""
        return bool(self.quality_rubric)

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
    "QualityRubricItem",
    "SlideCountRange",
    "SlideTypePolicy",
    "TextBudget",
    "VisibleTextPolicy",
    "VisibleTextRule",
]
