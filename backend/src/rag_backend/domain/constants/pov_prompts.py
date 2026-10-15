"""Prompt ids of the "Ponto de Vista" family (AE-0375, ADR-0021)."""

from __future__ import annotations

POV_PROMPT_DOMAIN = "carousel_pov"
POV_PROMPT_VERSION = "v1"
POV_PROMPT_OUTLINE = "outline"
POV_PROMPT_HOOK = "hook"
POV_PROMPT_CONTENT = "content"
POV_PROMPT_CAPTION = "caption"
HOOK_CANDIDATE_COUNT = 5
# AE-0376: the Radar IA v7 prompts (hero_lower_third_v4 projects).
RADAR_PROMPT_DOMAIN = "carousel"
RADAR_PROMPT_VERSION = "v7"
RADAR_PROMPT_OUTLINE = "outline"
RADAR_PROMPT_HOOK = "hook"
RADAR_PROMPT_CONTENT = "content"
# Outline slide-1 keys: the hook candidates and the outline checks.
OUTLINE_FIELD_HOOK_CANDIDATES = "hook_candidates"
OUTLINE_FIELD_OUTLINE_CHECKS = "outline_checks"
OUTLINE_CHECK_THESIS_EARLY = "thesis_early"

__all__ = [
    "HOOK_CANDIDATE_COUNT",
    "OUTLINE_CHECK_THESIS_EARLY",
    "OUTLINE_FIELD_HOOK_CANDIDATES",
    "OUTLINE_FIELD_OUTLINE_CHECKS",
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
