"""OpenAI image-prompt sanitizer — FALLBACK safety net.

OpenAI's moderation system flags photorealistic depictions of real brands,
people, and controversial events. The PRIMARY defense is the content-generation
prompt (``agents/prompts/carousel/v1/content_prompt.yaml``), which instructs
the LLM to avoid naming real-world brands, celebrities, or company logos in
``image_prompt`` and to use generic analogies instead.

This module exists as a SECONDARY fallback: it catches any trigger words that
still slip through despite the prompt instruction. The hardcoded map below is
for known, high-frequency triggers. **Do not add new brands here** — improve
the prompt instructions instead so the LLM generalizes to any brand.

Applied ONLY to OpenAI providers (gpt-image-2). Gemini's comic-neon style
is already abstract enough that it rarely hits the same filters.
"""

from __future__ import annotations

import re

# Fallback map for known trigger words that the LLM prompt may miss.
# Keys are lower-cased; matching is case-insensitive.
# Values are the replacement text.
# NOTE: Prefer updating the prompt template over expanding this map.
#       The prompt generalizes to any brand; this map only catches
#       specific slips.
_ANALOGY_MAP: dict[str, str] = {
    # People
    "elon musk": "a tech CEO",
    "musk": "a tech CEO",
    "jeff bezos": "an e-commerce founder",
    "mark zuckerberg": "a social media founder",
    "sam altman": "an AI lab director",
    "sundar pichai": "a search engine CEO",
    "tim cook": "a consumer electronics CEO",
    "satya nadella": "a cloud computing CEO",
    # Companies / brands
    "spacex": "a space exploration company",
    "cursor": "an AI coding tool",
    "openai": "an AI research lab",
    "anthropic": "an AI safety lab",
    "google": "a search engine giant",
    "alphabet": "a tech conglomerate",
    "microsoft": "a software corporation",
    "apple": "a consumer electronics firm",
    "amazon": "an e-commerce giant",
    "meta": "a social media conglomerate",
    "facebook": "a social network",
    "instagram": "a photo-sharing platform",
    "twitter": "a microblogging platform",
    "x.com": "a social platform",
    "tesla": "an electric vehicle maker",
    "nvidia": "a chip manufacturer",
    "intel": "a processor company",
    "amd": "a semiconductor firm",
    # Political / controversial
    "donald trump": "a political figure",
    "joe biden": "a political figure",
    "putin": "a world leader",
    "xi jinping": "a world leader",
    "kim jong-un": "a world leader",
    # Weapons / military (often flagged in photoreal)
    "missile": "a rocket",
    "nuclear": "energy core",
    "war": "conflict",
    "battle": "confrontation",
    # Drugs / adult content words that sometimes slip in
    "cocaine": "white powder",
    "heroin": "substance",
}

# Compile a single regex that matches any of the keys as whole words.
# We sort by length (longest first) so "elon musk" matches before "musk".
_sorted_keys = sorted(_ANALOGY_MAP.keys(), key=len, reverse=True)
_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _sorted_keys) + r")\b",
    re.IGNORECASE,
)


def sanitize_image_prompt(scene: str) -> str:
    """Return a moderation-safe version of an image prompt.

    Replaces real brands, people, and controversial terms with generic
    analogies. Preserves the overall scene description and cinematic
    style.

    This is a FALLBACK. The primary defense is the LLM prompt that
    generates ``image_prompt`` — it should already avoid naming brands
    and celebrities.
    """

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1).lower()
        return _ANALOGY_MAP.get(key, match.group(0))

    return _PATTERN.sub(_replace, scene)
