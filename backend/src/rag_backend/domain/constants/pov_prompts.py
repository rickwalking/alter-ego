"""Prompt ids of the "Ponto de Vista" family (ADR-0021).

``POV_NEWS_PROMPT_DOMAIN`` is the news-analysis voice of the family (ADR-0023):
same prompt names and version as ``carousel_pov``, only the domain differs. The
``RADAR_*`` ids are the Radar IA v7 prompts used by ``hero_lower_third_v4``
projects. ``PERSONA_POV_*`` name the persona block of the POV outline; a project
with no persona gets the explicit empty ``NO_PERSONA_CONTEXT``.
"""

from __future__ import annotations

POV_PROMPT_DOMAIN = "carousel_pov"
POV_PROMPT_VERSION = "v1"
POV_PROMPT_OUTLINE = "outline"
POV_PROMPT_HOOK = "hook"
POV_PROMPT_CONTENT = "content"
POV_PROMPT_CAPTION = "caption"
POV_NEWS_PROMPT_DOMAIN = "carousel_pov_news"
HOOK_CANDIDATE_COUNT = 5
RADAR_PROMPT_DOMAIN = "carousel"
RADAR_PROMPT_VERSION = "v7"
RADAR_PROMPT_OUTLINE = "outline"
RADAR_PROMPT_HOOK = "hook"
RADAR_PROMPT_CONTENT = "content"
OUTLINE_FIELD_HOOK_CANDIDATES = "hook_candidates"
OUTLINE_FIELD_OUTLINE_CHECKS = "outline_checks"
OUTLINE_CHECK_THESIS_EARLY = "thesis_early"
PERSONA_POV_PROMPT_DOMAIN = "persona_pov"
PERSONA_POV_PROMPT_CONTEXT = "context"
PERSONA_POV_PROMPT_VERSION = "v1"
NO_PERSONA_CONTEXT = ""
NO_PHRASES = "nenhuma"

__all__ = [
    "HOOK_CANDIDATE_COUNT",
    "NO_PERSONA_CONTEXT",
    "NO_PHRASES",
    "OUTLINE_CHECK_THESIS_EARLY",
    "OUTLINE_FIELD_HOOK_CANDIDATES",
    "OUTLINE_FIELD_OUTLINE_CHECKS",
    "PERSONA_POV_PROMPT_CONTEXT",
    "PERSONA_POV_PROMPT_DOMAIN",
    "PERSONA_POV_PROMPT_VERSION",
    "POV_NEWS_PROMPT_DOMAIN",
    "POV_PROMPT_CAPTION",
    "POV_PROMPT_CONTENT",
    "POV_PROMPT_DOMAIN",
    "POV_PROMPT_HOOK",
    "POV_PROMPT_OUTLINE",
    "POV_PROMPT_VERSION",
    "RADAR_PROMPT_CONTENT",
    "RADAR_PROMPT_DOMAIN",
    "RADAR_PROMPT_HOOK",
    "RADAR_PROMPT_OUTLINE",
    "RADAR_PROMPT_VERSION",
]
