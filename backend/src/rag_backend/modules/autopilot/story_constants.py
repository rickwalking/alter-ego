"""Instagram Story and music-nudge constants (AE-0369).

Kept beside ``constants.py`` so neither file exceeds the 400-line limit.
"""

from __future__ import annotations

from typing import Final

from rag_backend.domain.constants import IMAGE_STYLE_CINEMATIC, IMAGE_STYLE_COMIC_NEON

# One row per carousel in ``instagram_stories``: the Story's idempotency key.
TABLE_INSTAGRAM_STORIES = "instagram_stories"
FK_STORY_PROJECT = "fk_instagram_stories_carousel_project"
STORY_STATE_PENDING = "pending"
STORY_STATE_PUBLISHED = "published"
STORY_STATE_FAILED = "failed"
# What the owner notice says about the Story. A publisher that cannot post
# Stories (not the Graph publisher) sends no Story line at all.
STORY_OUTCOME_PUBLISHED = "published"
STORY_OUTCOME_FAILED = "failed"
# Graph calls per Story step: the first try plus two retries on transient errors.
STORY_MAX_ATTEMPTS = 3
REASON_STORY_IMAGE_MISSING = "story_image_missing"
REASON_STORY_CAROUSEL_MISSING = "story_carousel_missing"
REASON_STORY_UNEXPECTED = "story_unexpected_error"
LOG_STORY_FAILED = "autopilot_story_failed"
LOG_STORY_PUBLISHED = "autopilot_story_published"

# Outbox payload keys on ``content.autopilot.publish_notice``.
PAYLOAD_STORY_STATUS = "story_status"
PAYLOAD_STORY_ERROR = "story_error"
PAYLOAD_MUSIC_STYLE = "music_style"

# The owner's Telegram notice after a publish.
TEXT_PUBLISHED_PT = "✅ Publicado: {permalink}"
TEXT_PUBLISHED_PT_NO_LINK = "✅ Publicado"
TEXT_STORY_PUBLISHED = "\U0001f4f2 Story: publicado"
TEXT_STORY_FAILED = "\U0001f4f2 Story falhou: {reason}"
TEXT_MUSIC_NUDGE = "\U0001f3b5 Adicione uma música pelo app (20s): sugestão: {style}"
NOTICE_LINE_SEPARATOR = "\n"

# Music suggestion: niche words first, then the image style, then the default.
MUSIC_SYNTHWAVE = "lo-fi eletrônico / synthwave"
MUSIC_DARK_SYNTH = "dark synth"
MUSIC_CINEMATIC = "cinematic electronic"
MUSIC_DEFAULT = "lo-fi beats"
# Whole words, lowercased, accents stripped. ``ia`` is Portuguese for AI.
MUSIC_NICHE_WORDS: tuple[tuple[frozenset[str], str], ...] = (
    (
        frozenset({"cybersecurity", "ciberseguranca", "seguranca", "hacking"}),
        MUSIC_DARK_SYNTH,
    ),
    (frozenset({"robotics", "robotica", "robots", "robos"}), MUSIC_CINEMATIC),
    (
        frozenset({
            "ai",
            "ia",
            "artificial",
            "tech",
            "tecnologia",
            "technology",
            "llm",
            "llms",
            "software",
            "programacao",
            "dev",
        }),
        MUSIC_SYNTHWAVE,
    ),
)
MUSIC_IMAGE_STYLES: dict[str, str] = {
    IMAGE_STYLE_COMIC_NEON: MUSIC_SYNTHWAVE,
    IMAGE_STYLE_CINEMATIC: MUSIC_CINEMATIC,
}
MUSIC_WORD_PATTERN = r"\w+"
# NFKD splits accented letters so the combining marks can be dropped.
MUSIC_NORMAL_FORM: Final = "NFKD"
