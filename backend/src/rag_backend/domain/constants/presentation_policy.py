"""Presentation policy version identifiers and loader error messages."""

PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1 = "hero_lower_third_v1"
# AE-0312: v2 adds PT casing rules + severity metadata + proper-noun list. New
# carousels are stamped v2 at creation; DEFAULT stays v1 so legacy NULL-version
# rows keep their current semantics on re-validation reads.
PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2 = "hero_lower_third_v2"
# AE-0366: v3 makes sentence case (PT + EN, items too) blocking, adds the
# objective quality-rubric rules (empty body, closing actions, summary points,
# untranslated EN, <strong>-only markup) and the LLM quality rubric itself.
# New carousels are stamped v3; v2 projects keep their frozen semantics.
PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V3 = "hero_lower_third_v3"
# AE-0374 (ADR-0021): v4 adds per-slide roles for the Radar IA angle (hook,
# one news slide, impact slides, optional twist, verdict) and stops generating
# artwork for the summary/closing. Stamped on new Radar IA carousels.
PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V4 = "hero_lower_third_v4"
# AE-0374: the "Ponto de Vista" contract (8-10 slides with roles).
PRESENTATION_POLICY_VERSION_POV_HOOK_V1 = "pov_hook_v1"
DEFAULT_PRESENTATION_POLICY_VERSION = PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1
CREATE_TIME_PRESENTATION_POLICY_VERSION = (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V3
)
# AE-0374: the contracts a NEW carousel is stamped with, by content mode
# (``create_time_policy_version``). CREATE_TIME_PRESENTATION_POLICY_VERSION
# stays v3: it is also the rubric source for projects without a stamp.
CREATE_TIME_NEWS_PRESENTATION_POLICY_VERSION = (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V4
)
CREATE_TIME_POV_PRESENTATION_POLICY_VERSION = PRESENTATION_POLICY_VERSION_POV_HOOK_V1

ERR_PRESENTATION_POLICY_NOT_FOUND = "presentation_policy_not_found"
ERR_PRESENTATION_POLICY_INVALID = "presentation_policy_invalid"
ERR_PRESENTATION_POLICY_VERSION_UNKNOWN = "presentation_policy_version_unknown"
ERR_PRESENTATION_POLICY_RULE_SEVERITY_MISSING = (
    "presentation_policy_rule_severity_missing"
)

SUPPORTED_PRESENTATION_POLICY_VERSIONS: frozenset[str] = frozenset({
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1,
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2,
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V3,
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V4,
    PRESENTATION_POLICY_VERSION_POV_HOOK_V1,
})

CONTRACTS_SUBDIR = "contracts"
POLICY_FILE_SUFFIX = ".yaml"

__all__ = [
    "CONTRACTS_SUBDIR",
    "CREATE_TIME_NEWS_PRESENTATION_POLICY_VERSION",
    "CREATE_TIME_POV_PRESENTATION_POLICY_VERSION",
    "CREATE_TIME_PRESENTATION_POLICY_VERSION",
    "DEFAULT_PRESENTATION_POLICY_VERSION",
    "ERR_PRESENTATION_POLICY_INVALID",
    "ERR_PRESENTATION_POLICY_NOT_FOUND",
    "ERR_PRESENTATION_POLICY_RULE_SEVERITY_MISSING",
    "ERR_PRESENTATION_POLICY_VERSION_UNKNOWN",
    "POLICY_FILE_SUFFIX",
    "PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1",
    "PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2",
    "PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V3",
    "PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V4",
    "PRESENTATION_POLICY_VERSION_POV_HOOK_V1",
    "SUPPORTED_PRESENTATION_POLICY_VERSIONS",
]
