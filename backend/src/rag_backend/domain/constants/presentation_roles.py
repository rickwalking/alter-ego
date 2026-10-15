"""Per-slide roles on top of the five slide types (AE-0374, ADR-0021).

A contract may give each slide a ``role``. The role picks the prompt guidance
and the layout; the ``slide_type`` it maps to keeps every validator, casing
rule and translator working unchanged.
"""

from __future__ import annotations

from rag_backend.domain.constants.carousel import (
    SLIDE_TYPE_CLOSING,
    SLIDE_TYPE_CONTENT,
    SLIDE_TYPE_CTA,
    SLIDE_TYPE_INTRO,
    SLIDE_TYPE_SUMMARY,
)

ROLE_HOOK = "hook"
ROLE_REHOOK = "rehook"
ROLE_POV = "pov"
ROLE_POINT = "point"
ROLE_TWIST = "twist"
ROLE_SAVE = "save"
ROLE_CTA = "cta"
# Radar IA (hero_lower_third_v4).
ROLE_NEWS = "news"
ROLE_IMPACT = "impact"
ROLE_VERDICT = "verdict"

ROLE_SLIDE_TYPES: dict[str, frozenset[str]] = {
    ROLE_HOOK: frozenset({SLIDE_TYPE_INTRO}),
    ROLE_REHOOK: frozenset({SLIDE_TYPE_CONTENT}),
    ROLE_POV: frozenset({SLIDE_TYPE_CONTENT}),
    ROLE_POINT: frozenset({SLIDE_TYPE_CONTENT}),
    ROLE_TWIST: frozenset({SLIDE_TYPE_CONTENT}),
    ROLE_SAVE: frozenset({SLIDE_TYPE_SUMMARY}),
    ROLE_CTA: frozenset({SLIDE_TYPE_CTA}),
    ROLE_NEWS: frozenset({SLIDE_TYPE_SUMMARY}),
    ROLE_IMPACT: frozenset({SLIDE_TYPE_CONTENT}),
    ROLE_VERDICT: frozenset({SLIDE_TYPE_CLOSING}),
}
KNOWN_ROLES: frozenset[str] = frozenset(ROLE_SLIDE_TYPES)

# AE-0375: deck-level POV rubric rule codes. A rule fires only when the
# contract declares its severity (``pov_hook_v1``), so Radar IA v4 is unchanged.
VIOLATION_HOOK_WORD_LIMIT = "hook_word_limit"
VIOLATION_FIRST_PERSON_MISSING = "first_person_missing"

__all__ = [
    "KNOWN_ROLES",
    "ROLE_CTA",
    "ROLE_HOOK",
    "ROLE_IMPACT",
    "ROLE_NEWS",
    "ROLE_POINT",
    "ROLE_POV",
    "ROLE_REHOOK",
    "ROLE_SAVE",
    "ROLE_SLIDE_TYPES",
    "ROLE_TWIST",
    "ROLE_VERDICT",
    "VIOLATION_FIRST_PERSON_MISSING",
    "VIOLATION_HOOK_WORD_LIMIT",
]
