"""Presentation policy version identifiers and loader error messages.

- v1: the ``DEFAULT``, so legacy NULL-version rows keep their semantics on
  re-validation reads.
- v2: adds PT casing rules, severity metadata and a proper-noun list.
- v3: makes sentence case (PT + EN, items too) blocking and adds the objective
  quality-rubric rules (empty body, closing actions, summary points,
  untranslated EN, ``<strong>``-only markup) plus the LLM quality rubric. Older
  projects keep their frozen semantics.
- v4: per-slide roles for the Radar IA angle (hook, one news slide, impact
  slides, optional twist, verdict); no artwork for the summary/closing.
- ``pov_hook_v1``: the "Ponto de Vista" contract (8-10 slides with roles).

A NEW carousel is stamped by content mode (``create_time_policy_version``).
``CREATE_TIME_PRESENTATION_POLICY_VERSION`` stays v3 because it is also the
rubric source for projects without a stamp.
"""

PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1 = "hero_lower_third_v1"
PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V2 = "hero_lower_third_v2"
PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V3 = "hero_lower_third_v3"
PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V4 = "hero_lower_third_v4"
PRESENTATION_POLICY_VERSION_POV_HOOK_V1 = "pov_hook_v1"
DEFAULT_PRESENTATION_POLICY_VERSION = PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V1
CREATE_TIME_PRESENTATION_POLICY_VERSION = (
    PRESENTATION_POLICY_VERSION_HERO_LOWER_THIRD_V3
)
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
