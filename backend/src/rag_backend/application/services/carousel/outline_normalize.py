"""Normalize editorial outlines to the carousel contract.

Legacy outlines (no roles) keep the canonical seven-slide positional types.
An outline whose every slide carries a known ``role`` (stamped by
position from a ranged contract, ``stamp_outline_roles``) keeps its roles and
gets each role's slide type, up to ``MAX_SLIDES``.
"""

from __future__ import annotations

from rag_backend.application.services.carousel.editorial_distribution_constants import (
    OUTLINE_LEGACY_HEADING_KEY,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
)
from rag_backend.application.services.carousel.types import (
    LEGACY_SLIDE_COUNT,
    MAX_SLIDES,
)
from rag_backend.application.services.carousel.visible_copy_sanitize import (
    sanitize_visible_copy,
)
from rag_backend.domain.constants.carousel import (
    LANGUAGE_PT,
    SLIDE_TYPE_CLOSING,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_CTA,
    SLIDE_TYPE_INTRO,
    SLIDE_TYPE_SUMMARY,
)
from rag_backend.domain.constants.pov_prompts import (
    OUTLINE_FIELD_HOOK_CANDIDATES,
    OUTLINE_FIELD_OUTLINE_CHECKS,
)
from rag_backend.domain.constants.presentation_roles import (
    KNOWN_ROLES,
    ROLE_SLIDE_TYPES,
)

OUTLINE_FIELD_SLIDE_INDEX = "slide_index"
OUTLINE_FIELD_TITLE = "title"
OUTLINE_FIELD_KEY_POINTS = "key_points"
OUTLINE_FIELD_SLIDE_TYPE = "slide_type"
OUTLINE_FIELD_TLDR = "tldr_strip"
OUTLINE_FIELD_ROLE = "role"

_CANONICAL_SLIDE_TYPES: tuple[str, ...] = (
    SLIDE_TYPE_INTRO,
    SLIDE_TYPE_SUMMARY,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_CLOSING,
    SLIDE_TYPE_CTA,
)


def canonical_slide_type(slide_number: int) -> str:
    """Return the expected slide type for a 1-based slide index (1..7)."""
    if slide_number < 1:
        return SLIDE_TYPE_CONTENT
    index = min(slide_number, len(_CANONICAL_SLIDE_TYPES)) - 1
    return _CANONICAL_SLIDE_TYPES[index]


def _role_of(item: dict[str, object]) -> str | None:
    role = item.get(OUTLINE_FIELD_ROLE)
    return role if isinstance(role, str) and role in KNOWN_ROLES else None


def outline_has_roles(outline: list[dict[str, object]]) -> bool:
    """True when every slide carries a known role (a ranged-contract outline)."""
    return bool(outline) and all(_role_of(item) for item in outline)


def stamp_outline_roles(
    outline: list[dict[str, object]], policy: CarouselPresentationPolicy
) -> list[dict[str, object]]:
    """Give each slide the role and type of its position in ``policy``.

    Roles never come from the model (skeptical review #3): the expanded
    contract decides them by position. Slides past the contract's length are
    dropped; a contract without roles returns the outline unchanged.
    """
    if not policy.has_roles:
        return outline
    stamped: list[dict[str, object]] = []
    for item, slide in zip(outline, policy.slides, strict=False):
        stamped.append({
            **item,
            OUTLINE_FIELD_ROLE: slide.role,
            OUTLINE_FIELD_SLIDE_TYPE: slide.slide_type,
        })
    return stamped


def _slide_type_for(
    item: dict[str, object], slide_number: int, role: str | None
) -> str:
    if role is None:
        return canonical_slide_type(slide_number)
    stated = item.get(OUTLINE_FIELD_SLIDE_TYPE)
    allowed = ROLE_SLIDE_TYPES[role]
    if isinstance(stated, str) and stated in allowed:
        return stated
    return sorted(allowed)[0]


def _first_slide_extras(item: dict[str, object]) -> dict[str, object]:
    """Slide 1 keeps its hook candidates and outline checks."""
    extras: dict[str, object] = {}
    candidates = item.get(OUTLINE_FIELD_HOOK_CANDIDATES)
    if isinstance(candidates, list):
        cleaned = [
            sanitize_visible_copy(text, locale=LANGUAGE_PT)
            for text in candidates
            if isinstance(text, str)
        ]
        extras[OUTLINE_FIELD_HOOK_CANDIDATES] = [text for text in cleaned if text]
    checks = item.get(OUTLINE_FIELD_OUTLINE_CHECKS)
    if isinstance(checks, dict):
        extras[OUTLINE_FIELD_OUTLINE_CHECKS] = {
            str(key): value for key, value in checks.items() if isinstance(value, bool)
        }
    return extras


def normalize_editorial_outline(
    raw_outline: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Trim, renumber, and type the slides (legacy: 7 canonical; roles: by role)."""
    roles = outline_has_roles(raw_outline)
    limit = MAX_SLIDES if roles else LEGACY_SLIDE_COUNT
    normalized: list[dict[str, object]] = []
    for index, item in enumerate(raw_outline[:limit]):
        if not isinstance(item, dict):
            continue
        slide_number = index + 1
        role = _role_of(item) if roles else None
        title = sanitize_visible_copy(
            item.get(OUTLINE_FIELD_TITLE, "")
            or item.get(OUTLINE_LEGACY_HEADING_KEY, ""),
            locale=LANGUAGE_PT,
        )
        raw_points = item.get(OUTLINE_FIELD_KEY_POINTS, [])
        key_points: list[str] = []
        if isinstance(raw_points, list):
            for point in raw_points:
                cleaned = sanitize_visible_copy(point, locale=LANGUAGE_PT)
                if cleaned:
                    key_points.append(cleaned)
        slide: dict[str, object] = {
            OUTLINE_FIELD_SLIDE_INDEX: slide_number,
            OUTLINE_FIELD_TITLE: title,
            OUTLINE_FIELD_KEY_POINTS: key_points,
            OUTLINE_FIELD_SLIDE_TYPE: _slide_type_for(item, slide_number, role),
        }
        if role is not None:
            slide[OUTLINE_FIELD_ROLE] = role
        tldr = item.get(OUTLINE_FIELD_TLDR)
        if slide_number == 1:
            cleaned_tldr = sanitize_visible_copy(tldr, locale=LANGUAGE_PT)
            if cleaned_tldr:
                slide[OUTLINE_FIELD_TLDR] = cleaned_tldr
            slide.update(_first_slide_extras(item))
        normalized.append(slide)
    return normalized


__all__ = [
    "canonical_slide_type",
    "normalize_editorial_outline",
]
