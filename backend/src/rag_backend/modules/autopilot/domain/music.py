"""The "add music" suggestion for a published carousel (AE-0369). Pure.

The Graph API cannot add music to a feed post, so the owner gets a style to
pick in the app. Niche words win over the image style; anything else gets
the default.
"""

from __future__ import annotations

import re
import unicodedata

from rag_backend.modules.autopilot.story_constants import (
    MUSIC_DEFAULT,
    MUSIC_IMAGE_STYLES,
    MUSIC_NICHE_WORDS,
    MUSIC_NORMAL_FORM,
    MUSIC_WORD_PATTERN,
)

_WORD = re.compile(MUSIC_WORD_PATTERN)


def music_style_for(niche: str, image_style: str) -> str:
    """The suggested music style for this niche and image preset."""
    words = _words(niche)
    for vocabulary, style in MUSIC_NICHE_WORDS:
        if words & vocabulary:
            return style
    return MUSIC_IMAGE_STYLES.get(image_style.strip().lower(), MUSIC_DEFAULT)


def _words(text: str) -> frozenset[str]:
    decomposed = unicodedata.normalize(MUSIC_NORMAL_FORM, text.lower())
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return frozenset(_WORD.findall(plain))
