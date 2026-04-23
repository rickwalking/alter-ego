"""OpenAI image-prompt sanitizer.

OpenAI's moderation system flags photorealistic depictions of real brands,
people, and controversial events. This module strips or replaces those
triggers with generic analogies so the scene stays intact but passes
moderation.

Applied ONLY to OpenAI providers (gpt-image-2). Gemini's comic-neon style
is already abstract enough that it rarely hits the same filters.
"""

from __future__ import annotations

import re

# Map known trigger words to generic analogies.
# Keys are lower-cased; matching is case-insensitive.
# Values are the replacement text.
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
    """

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1).lower()
        return _ANALOGY_MAP.get(key, match.group(0))

    return _PATTERN.sub(_replace, scene)
