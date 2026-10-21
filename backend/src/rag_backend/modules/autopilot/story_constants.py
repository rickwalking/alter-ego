"""Instagram Story and music-nudge constants.

Kept beside ``constants.py`` so neither file exceeds the 400-line limit.

- ``instagram_stories`` holds one row per carousel: the Story's idempotency key.
- A publisher that cannot post Stories (not the Graph publisher) sends no Story line in
  the owner notice.
- Each Story step makes the first Graph call plus two retries on transient errors.
- The music suggestion matches niche words first, then the image style, then falls back
  to the default. Words match whole, lowercased and with accents stripped (NFKD splits
  accented letters so the combining marks can be dropped); ``ia`` is Portuguese for AI.
"""

from __future__ import annotations

from typing import Final

from rag_backend.domain.constants import IMAGE_STYLE_CINEMATIC, IMAGE_STYLE_COMIC_NEON

TABLE_INSTAGRAM_STORIES = "instagram_stories"
FK_STORY_PROJECT = "fk_instagram_stories_carousel_project"
STORY_STATE_PENDING = "pending"
STORY_STATE_PUBLISHED = "published"
STORY_STATE_FAILED = "failed"
STORY_OUTCOME_PUBLISHED = "published"
STORY_OUTCOME_FAILED = "failed"
STORY_MAX_ATTEMPTS = 3
REASON_STORY_IMAGE_MISSING = "story_image_missing"
REASON_STORY_CAROUSEL_MISSING = "story_carousel_missing"
REASON_STORY_UNEXPECTED = "story_unexpected_error"
LOG_STORY_FAILED = "autopilot_story_failed"
LOG_STORY_PUBLISHED = "autopilot_story_published"

PAYLOAD_STORY_STATUS = "story_status"
PAYLOAD_STORY_ERROR = "story_error"
PAYLOAD_MUSIC_STYLE = "music_style"

TEXT_PUBLISHED_PT = "✅ Publicado: {permalink}"
TEXT_PUBLISHED_PT_NO_LINK = "✅ Publicado"
TEXT_STORY_PUBLISHED = "\U0001f4f2 Story: publicado"
TEXT_STORY_FAILED = "\U0001f4f2 Story falhou: {reason}"
TEXT_MUSIC_NUDGE = "\U0001f3b5 Adicione uma música pelo app (20s): sugestão: {style}"
NOTICE_LINE_SEPARATOR = "\n"

MUSIC_SYNTHWAVE = "lo-fi eletrônico / synthwave"
MUSIC_DARK_SYNTH = "dark synth"
MUSIC_CINEMATIC = "cinematic electronic"
MUSIC_DEFAULT = "lo-fi beats"
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
MUSIC_NORMAL_FORM: Final = "NFKD"
