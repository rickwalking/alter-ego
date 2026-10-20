"""Constants for the blog section editor routes (AE-0424, ADR-0025)."""

from typing import Final

# Content language of the edited document: PT is the top level, EN lives in
# ``content.translations.en`` (same shape). Independent of the UI locale.
BLOG_LANGUAGE_PT: Final = "pt"
BLOG_LANGUAGE_EN: Final = "en"
BLOG_EDITOR_LANGUAGE_PATTERN: Final = r"^(pt|en)$"

# Blog-images store: ``<carousel_output_dir>/blog-images/<post_id>/<uuid>.jpg``.
# The canonical same-origin URL is served by ``GET /api/blog-images/...``; a
# CDN URL is used instead when the CDN is enabled. A provider URL is never kept.
BLOG_IMAGES_DIR_NAME: Final = "blog-images"
# Provider bytes land in ``<uuid>.part``; the store sniffs the real type and
# renames (gpt-image-2 returns PNG by default). extension -> (offset, magic).
BLOG_IMAGE_PARTIAL_SUFFIX: Final = ".part"
BLOG_IMAGE_TYPES: Final[dict[str, tuple[int, bytes]]] = {
    "png": (0, b"\x89PNG\r\n\x1a\n"),
    "jpg": (0, b"\xff\xd8\xff"),
    "webp": (8, b"WEBP"),
}
# Never prune a store file younger than this: a concurrent generation may
# still be waiting on the row lock to store it (AE-0424 review round 2).
BLOG_IMAGE_PRUNE_GRACE_SECONDS: Final = 3600
BLOG_IMAGE_MEDIA_TYPES: Final[dict[str, str]] = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "webp": "image/webp",
}
BLOG_IMAGES_ROUTE_PREFIX: Final = "/api/blog-images"
BLOG_IMAGE_FILENAME_PATTERN: Final = (
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.(jpg|png|webp)$"
)
# Model recorded on a generated image (the gpt-image-2 OpenAI provider).
BLOG_IMAGE_MODEL: Final = "gpt-image-2"
# Published posts: cacheable but revalidated (an unpublish must take effect).
# Drafts: author/admin only, never stored by shared caches (ADR-0013).
BLOG_IMAGE_CACHE_PUBLIC: Final = "public, max-age=3600, must-revalidate"
BLOG_IMAGE_CACHE_PRIVATE: Final = "private, no-store"
# Per-post image budget (generate + regenerate count), BLOG_IMAGE_COST_CAP.
BLOG_IMAGE_GENERATIONS_KEY: Final = "blog_image_generations"

# Versioned prompt templates (agents/prompts/blog/v1/).
PROMPT_DOMAIN_BLOG: Final = "blog"
PROMPT_IMAGE: Final = "image_prompt"
PROMPT_TRANSLATE_SECTION: Final = "translate_section"
IMAGE_PROMPT_MAX_CHARS: Final = 2000
IMAGE_PROMPT_BODY_CHARS: Final = 600

# Langfuse phases.
PHASE_BLOG_SECTION_IMAGE: Final = "blog_section_image"
PHASE_BLOG_SECTION_REWRITE: Final = "blog_section_rewrite"
PHASE_BLOG_TRANSLATION: Final = "blog_translation"

# Version history entries (``blog_posts.version_history``).
VERSION_CONTENT_TYPE_BLOG_POST: Final = "blog_post"
# Entries snapshot the state BEFORE the write (AE-0424 review): the summary
# names the write that replaced it.
VERSION_SUMMARY_SAVE: Final = "Before save"
VERSION_SUMMARY_RESTORE: Final = "Before restoring version {version_number}"
VERSION_SUMMARY_SLOT: Final = "Before {action}"
# Bounded history: the first (original) entry + the newest ones.
BLOG_VERSION_HISTORY_MAX: Final = 50

# ai-suggest envelope keys (AE-0424 strict JSON, F-10).
SUGGEST_KEY_TEXT: Final = "suggested_text"
SUGGEST_KEY_EXPLANATION: Final = "explanation"
CODE_FENCE: Final = "```"

# Error codes (API ``detail``).
ERR_BLOG_SECTION_NOT_FOUND: Final = "blog_section_not_found"
ERR_BLOG_SECTION_IMAGE_MISSING: Final = "blog_section_image_missing"
ERR_BLOG_TRANSLATION_MISSING: Final = "blog_translation_missing"
ERR_BLOG_TRANSLATION_EXISTS: Final = "blog_translation_exists"
ERR_BLOG_IMAGE_PERSIST_FAILED: Final = "blog_image_persist_failed"
ERR_BLOG_IMAGE_GENERATION_FAILED: Final = "blog_image_generation_failed"
ERR_BLOG_IMAGE_NOT_FOUND: Final = "blog_image_not_found"
ERR_BLOG_IMAGE_BUDGET_EXHAUSTED: Final = "blog_image_budget_exhausted"
ERR_BLOG_REWRITE_TOO_LONG: Final = "blog_rewrite_too_long"
ERR_BLOG_PERSONA_REQUIRED: Final = "blog_persona_required"
ERR_BLOG_REWRITE_EMPTY: Final = "blog_rewrite_empty"
ERR_BLOG_TRANSLATION_FAILED: Final = "blog_translation_failed"
ERR_BLOG_SCHEDULE_NOT_SET: Final = "blog_schedule_not_set"
ERR_BLOG_REVIEWER_REQUIRED: Final = "blog_reviewer_required"
# AE-0438 (F-05): a stored snapshot with no content (pre-fix bootstrap) cannot
# be restored; the operator command ``blog_empty_versions`` repairs the history.
ERR_BLOG_VERSION_EMPTY: Final = "blog_version_empty"

# AE-0438 (F-08): the single-section rewrite must not echo the heading back as
# the first line of the body; this instruction goes to the persona enforce call.
REWRITE_NO_HEADING_INSTRUCTION: Final = (
    "Rewrite only the body of this section. Do not repeat the heading above as "
    "a title, a heading, a bold line or a plain line. Start directly with the "
    "body text and return only the body text."
)
