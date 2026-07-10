"""Load canonical carousel presentation policy from packaged runtime contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import cast

import yaml

from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
    CasingRulePolicy,
    FontPolicy,
    GeometryBudget,
    PresentationPolicyError,
    SlideTypePolicy,
    TextBudget,
    VisibleTextPolicy,
    VisibleTextRule,
)
from rag_backend.domain.constants.carousel_presentation import (
    VALID_VIOLATION_SEVERITIES,
)
from rag_backend.domain.constants.presentation_policy import (
    CONTRACTS_SUBDIR,
    DEFAULT_PRESENTATION_POLICY_VERSION,
    ERR_PRESENTATION_POLICY_INVALID,
    ERR_PRESENTATION_POLICY_NOT_FOUND,
    ERR_PRESENTATION_POLICY_RULE_SEVERITY_MISSING,
    POLICY_FILE_SUFFIX,
    SUPPORTED_PRESENTATION_POLICY_VERSIONS,
)
from rag_backend.domain.constants.runtime_skills import (
    CAROUSEL_PIPELINE_SKILL_ID,
    resolve_runtime_skill_filesystem_path,
)
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_POLICY_KEY_RULE_SEVERITIES = "rule_severities"
_POLICY_KEY_CASING = "casing"
_POLICY_KEY_CASING_RULES = "rules"
_POLICY_KEY_CASING_PROPER_NOUNS = "proper_nouns"
_POLICY_KEY_CASING_RULE_CODE = "code"
_POLICY_KEY_CASING_EXEMPT_SLIDE_TYPES = "exempt_slide_types"

POLICY_CHECKSUM_PREFIX = "sha256"
POLICY_CONTEXT_HEADER = "Presentation policy"
POLICY_CONTEXT_SECTION_RULES = "Visible text rules"
POLICY_CONTEXT_SECTION_BUDGETS = "Copy budgets"
POLICY_CONTEXT_SECTION_GEOMETRY = "Geometry ratios"
POLICY_CONTEXT_SECTION_ICONS = "Lucide icon allowlist"


def load_presentation_policy(version: str) -> CarouselPresentationPolicy:
    """Load and validate a versioned presentation policy contract.

    AE-0312 rollback safety: an unsupported version falls back to the default
    (v1) with a warning log and never raises, so a code rollback after the
    in-flight upgrade migration cannot freeze v2-stamped rows.
    """
    resolved_version = version
    if resolved_version not in SUPPORTED_PRESENTATION_POLICY_VERSIONS:
        logger.warning(
            "presentation_policy_version_unsupported",
            requested_version=version,
            fallback_version=DEFAULT_PRESENTATION_POLICY_VERSION,
        )
        resolved_version = DEFAULT_PRESENTATION_POLICY_VERSION

    path = resolve_runtime_skill_filesystem_path(
        CAROUSEL_PIPELINE_SKILL_ID,
        CONTRACTS_SUBDIR,
        f"{resolved_version}{POLICY_FILE_SUFFIX}",
    )
    if not path.is_file():
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_NOT_FOUND)

    raw_text = path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(raw_text)
    if not isinstance(parsed, dict):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)

    return _parse_policy_document(cast(dict[str, object], parsed), raw_text)


def policy_checksum(raw_yaml: str) -> str:
    """Return a stable SHA-256 checksum for canonical policy YAML bytes."""
    digest = sha256(raw_yaml.encode("utf-8")).hexdigest()
    return f"{POLICY_CHECKSUM_PREFIX}-{digest}"


def render_presentation_policy_context(policy: CarouselPresentationPolicy) -> str:
    """Render a prompt-safe policy fragment from typed policy values."""
    slide_lines = [
        f"{slide.slide_number}: {slide.slide_type}"
        + (
            f" (copy_start_ratio={slide.copy_start_ratio})"
            if slide.copy_start_ratio is not None
            else ""
        )
        for slide in policy.slides
    ]
    rule_lines = [
        f"- {rule.rule_id}: {rule.summary}" for rule in policy.visible_text.rules
    ]
    budget_lines = [
        _format_budget(field_name, budget)
        for field_name, budget in sorted(policy.copy_budgets.items())
    ]
    icon_lines = [f"- {icon_name}" for icon_name in policy.lucide_icon_allowlist]
    ratio_lines = [
        f"- {slide.slide_type}: {slide.copy_start_ratio}"
        for slide in policy.slides
        if slide.copy_start_ratio is not None
    ]
    sections = [
        f"{POLICY_CONTEXT_HEADER}: {policy.version}",
        f"Slide count: {policy.slide_count}",
        "Slide sequence:",
        *[f"  {line}" for line in slide_lines],
        f"Artwork slides: {', '.join(str(number) for number in policy.artwork_slides)}",
        f"CTA avatar required: {policy.cta_avatar_required}",
        POLICY_CONTEXT_SECTION_RULES + ":",
        *rule_lines,
        POLICY_CONTEXT_SECTION_BUDGETS + ":",
        *budget_lines,
        POLICY_CONTEXT_SECTION_GEOMETRY + ":",
        f"- viewport_standard: {policy.geometry.viewport_standard_width}x"
        f"{policy.geometry.viewport_standard_height}",
        f"- viewport_hd: {policy.geometry.viewport_hd_width}x"
        f"{policy.geometry.viewport_hd_height}",
        *ratio_lines,
        POLICY_CONTEXT_SECTION_ICONS + ":",
        *icon_lines,
    ]
    return "\n".join(sections)


def _format_budget(field_name: str, budget: TextBudget) -> str:
    if budget.max_lines is None:
        return f"- {field_name}: max {budget.max_characters} characters"
    return (
        f"- {field_name}: max {budget.max_characters} characters, "
        f"max {budget.max_lines} rendered lines"
    )


def _parse_policy_document(
    document: dict[str, object],
    raw_yaml: str,
) -> CarouselPresentationPolicy:
    version = _require_str(document, "version")
    slide_count = _require_int(document, "slide_count")
    slides = _parse_slide_sequence(document.get("slide_sequence"))
    artwork_slides, cta_avatar_required = _parse_image_scope(document)
    visible_text = _parse_visible_text(document.get("visible_text_rules"))
    copy_budgets = _parse_copy_budgets(document.get("copy_budgets"))
    geometry = _parse_geometry(document.get("geometry"))
    lucide_icons = _parse_str_tuple(document.get("lucide_icon_allowlist"))
    fonts = _parse_fonts(document.get("fonts"))
    lowercase_allowlist = _parse_str_tuple(
        document.get("intentional_lowercase_allowlist")
    )
    casing = _parse_casing_metadata(document)

    if len(slides) != slide_count:
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)

    return CarouselPresentationPolicy(
        version=version,
        slide_count=slide_count,
        slides=slides,
        artwork_slides=artwork_slides,
        cta_avatar_required=cta_avatar_required,
        visible_text=visible_text,
        copy_budgets=copy_budgets,
        geometry=geometry,
        lucide_icon_allowlist=lucide_icons,
        fonts=fonts,
        intentional_lowercase_allowlist=lowercase_allowlist,
        checksum=policy_checksum(raw_yaml),
        rule_severities=casing.rule_severities,
        casing_rules=casing.casing_rules,
        proper_nouns=casing.proper_nouns,
    )


def _parse_image_scope(document: dict[str, object]) -> tuple[tuple[int, ...], bool]:
    """Parse the ``image_scope`` block into (artwork_slides, cta_avatar_required)."""
    image_scope = _require_mapping(document, "image_scope")
    artwork_slides = _parse_int_tuple(image_scope.get("artwork_slides"))
    cta_avatar_required = bool(image_scope.get("cta_avatar_required", False))
    return artwork_slides, cta_avatar_required


@dataclass(frozen=True)
class _CasingMetadata:
    """Parsed severity + casing metadata (empty for v1 policies)."""

    rule_severities: dict[str, str]
    casing_rules: tuple[CasingRulePolicy, ...]
    proper_nouns: tuple[str, ...]


def _parse_casing_metadata(document: dict[str, object]) -> _CasingMetadata:
    """Parse severities + casing rules and assert v2 severity completeness."""
    rule_severities = _parse_rule_severities(document.get(_POLICY_KEY_RULE_SEVERITIES))
    casing_rules, proper_nouns = _parse_casing(document.get(_POLICY_KEY_CASING))
    _assert_casing_rules_have_severity(casing_rules, rule_severities)
    return _CasingMetadata(
        rule_severities=rule_severities,
        casing_rules=casing_rules,
        proper_nouns=proper_nouns,
    )


def _parse_rule_severities(raw_value: object) -> dict[str, str]:
    """Parse the ``rule_severities`` map, validating every declared severity."""
    if raw_value is None:
        return {}
    if not isinstance(raw_value, dict):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    severities: dict[str, str] = {}
    for code, severity in cast(dict[str, object], raw_value).items():
        if not isinstance(severity, str) or severity not in VALID_VIOLATION_SEVERITIES:
            raise PresentationPolicyError(ERR_PRESENTATION_POLICY_RULE_SEVERITY_MISSING)
        severities[str(code)] = severity
    return severities


def _parse_casing(
    raw_value: object,
) -> tuple[tuple[CasingRulePolicy, ...], tuple[str, ...]]:
    """Parse the optional ``casing`` section (v2+); v1 policies omit it."""
    if raw_value is None:
        return (), ()
    if not isinstance(raw_value, dict):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    mapping = cast(dict[str, object], raw_value)
    proper_nouns = _parse_str_tuple(mapping.get(_POLICY_KEY_CASING_PROPER_NOUNS))
    raw_rules = mapping.get(_POLICY_KEY_CASING_RULES)
    if not isinstance(raw_rules, list):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    rules = tuple(_parse_casing_rule(item) for item in raw_rules)
    return rules, proper_nouns


def _parse_casing_rule(item: object) -> CasingRulePolicy:
    if not isinstance(item, dict):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    mapping = cast(dict[str, object], item)
    code = _require_str(mapping, _POLICY_KEY_CASING_RULE_CODE)
    exempt = mapping.get(_POLICY_KEY_CASING_EXEMPT_SLIDE_TYPES, [])
    if not isinstance(exempt, list):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    return CasingRulePolicy(
        code=code,
        exempt_slide_types=frozenset(str(value) for value in exempt),
    )


def _assert_casing_rules_have_severity(
    casing_rules: tuple[CasingRulePolicy, ...],
    rule_severities: dict[str, str],
) -> None:
    """Fail load when a v2 casing rule carries no explicit severity (AE-0312)."""
    for rule in casing_rules:
        if rule.code not in rule_severities:
            raise PresentationPolicyError(ERR_PRESENTATION_POLICY_RULE_SEVERITY_MISSING)


def _parse_slide_sequence(raw_value: object) -> tuple[SlideTypePolicy, ...]:
    if not isinstance(raw_value, list):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    slides: list[SlideTypePolicy] = []
    for item in raw_value:
        if not isinstance(item, dict):
            raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
        mapping = cast(dict[str, object], item)
        ratio_value = mapping.get("copy_start_ratio")
        copy_start_ratio = float(ratio_value) if ratio_value is not None else None
        slides.append(
            SlideTypePolicy(
                slide_number=_require_int(mapping, "slide_number"),
                slide_type=_require_str(mapping, "slide_type"),
                image_required=bool(mapping.get("image_required", False)),
                copy_start_ratio=copy_start_ratio,
                avatar_required=bool(mapping.get("avatar_required", False)),
            )
        )
    return tuple(slides)


def _parse_visible_text(raw_value: object) -> VisibleTextPolicy:
    if not isinstance(raw_value, list):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    rules: list[VisibleTextRule] = []
    for item in raw_value:
        if not isinstance(item, dict):
            raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
        mapping = cast(dict[str, object], item)
        rules.append(
            VisibleTextRule(
                rule_id=_require_str(mapping, "rule_id"),
                summary=_require_str(mapping, "summary"),
            )
        )
    return VisibleTextPolicy(rules=tuple(rules))


def _parse_copy_budgets(raw_value: object) -> dict[str, TextBudget]:
    if not isinstance(raw_value, dict):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    budgets: dict[str, TextBudget] = {}
    for field_name, item in cast(dict[str, object], raw_value).items():
        if not isinstance(item, dict):
            raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
        mapping = cast(dict[str, object], item)
        max_lines_value = mapping.get("max_lines")
        max_lines = int(max_lines_value) if max_lines_value is not None else None
        budgets[field_name] = TextBudget(
            max_characters=_require_int(mapping, "max_characters"),
            max_lines=max_lines,
        )
    return budgets


def _parse_geometry(raw_value: object) -> GeometryBudget:
    if not isinstance(raw_value, dict):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    mapping = cast(dict[str, object], raw_value)
    standard = _require_mapping(mapping, "viewport_standard")
    hd = _require_mapping(mapping, "viewport_hd")
    selectors_raw = mapping.get("selectors")
    if not isinstance(selectors_raw, dict):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    selectors = {
        str(key): str(value)
        for key, value in cast(dict[str, object], selectors_raw).items()
    }
    return GeometryBudget(
        viewport_standard_width=_require_int(standard, "width"),
        viewport_standard_height=_require_int(standard, "height"),
        viewport_hd_width=_require_int(hd, "width"),
        viewport_hd_height=_require_int(hd, "height"),
        footer_gap_standard=_require_int(mapping, "footer_gap_standard"),
        footer_gap_hd=_require_int(mapping, "footer_gap_hd"),
        tolerance_standard=_require_int(mapping, "tolerance_standard"),
        tolerance_hd=_require_int(mapping, "tolerance_hd"),
        near_limit_standard=_require_int(mapping, "near_limit_standard"),
        near_limit_hd=_require_int(mapping, "near_limit_hd"),
        selectors=selectors,
    )


def _parse_fonts(raw_value: object) -> FontPolicy:
    if not isinstance(raw_value, dict):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    mapping = cast(dict[str, object], raw_value)
    return FontPolicy(
        heading_family=_require_str(mapping, "heading_family"),
        body_family=_require_str(mapping, "body_family"),
        badge_family=_require_str(mapping, "badge_family"),
    )


def _parse_int_tuple(raw_value: object) -> tuple[int, ...]:
    if not isinstance(raw_value, list):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    return tuple(int(item) for item in raw_value)


def _parse_str_tuple(raw_value: object) -> tuple[str, ...]:
    if not isinstance(raw_value, list):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    return tuple(str(item) for item in raw_value)


def _require_mapping(document: dict[str, object], key: str) -> dict[str, object]:
    value = document.get(key)
    if not isinstance(value, dict):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    return cast(dict[str, object], value)


def _require_str(document: dict[str, object], key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    return value


def _require_int(document: dict[str, object], key: str) -> int:
    value = document.get(key)
    if not isinstance(value, int):
        raise PresentationPolicyError(ERR_PRESENTATION_POLICY_INVALID)
    return value


def canonical_policy_json(policy: CarouselPresentationPolicy) -> str:
    """Serialize typed policy values for drift-test comparisons."""
    payload = {
        "version": policy.version,
        "slide_count": policy.slide_count,
        "slides": [
            {
                "slide_number": slide.slide_number,
                "slide_type": slide.slide_type,
                "image_required": slide.image_required,
                "copy_start_ratio": slide.copy_start_ratio,
                "avatar_required": slide.avatar_required,
            }
            for slide in policy.slides
        ],
        "artwork_slides": list(policy.artwork_slides),
        "cta_avatar_required": policy.cta_avatar_required,
        "visible_text_rule_ids": [rule.rule_id for rule in policy.visible_text.rules],
        "copy_budgets": {
            field_name: {
                "max_characters": budget.max_characters,
                "max_lines": budget.max_lines,
            }
            for field_name, budget in policy.copy_budgets.items()
        },
        "geometry": {
            "viewport_standard_width": policy.geometry.viewport_standard_width,
            "viewport_standard_height": policy.geometry.viewport_standard_height,
            "viewport_hd_width": policy.geometry.viewport_hd_width,
            "viewport_hd_height": policy.geometry.viewport_hd_height,
            "copy_start_ratios": {
                slide.slide_type: slide.copy_start_ratio
                for slide in policy.slides
                if slide.copy_start_ratio is not None
            },
        },
        "lucide_icon_allowlist": list(policy.lucide_icon_allowlist),
    }
    return json.dumps(payload, sort_keys=True)


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
    "canonical_policy_json",
    "load_presentation_policy",
    "policy_checksum",
    "render_presentation_policy_context",
]
