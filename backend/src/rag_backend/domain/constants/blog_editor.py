"""Constants for the blog section editor routes (ADR-0025).

The edited document's content language is independent of the UI locale: PT is the top
level and EN lives in ``content.translations.en`` with the same shape. Images are stored
at ``<carousel_output_dir>/blog-images/<post_id>/<uuid>.jpg`` and served same-origin by
``GET /api/blog-images/...`` (or from the CDN when enabled); a provider URL is never
kept. Provider bytes land in ``<uuid>.part`` and the store sniffs the real type
(extension to offset and magic) before renaming, since gpt-image-2 returns PNG by
default. A store file younger than the prune grace period is never pruned, because a
concurrent generation may still be waiting on the row lock to store it. Published images
are cacheable but revalidated (an unpublish must take effect); drafts are author/admin
only and never stored by shared caches. A draft-image 404 is ``no-store``: Cloudflare's
default browser TTL is 14400 s, so a cached 404 would outlive a later publish. The
per-post image budget counts generations and regenerations. Version-history entries
snapshot the state before the write, and the summary names the write that replaced it;
the history keeps the first entry plus the newest ones. A stored snapshot with no
content cannot be restored (the ``blog_empty_versions`` operator command repairs such
history). The single-section rewrite must not echo the heading as the first body line;
that instruction goes to the persona enforce call.
"""

from typing import Final

BLOG_LANGUAGE_PT: Final = "pt"
BLOG_LANGUAGE_EN: Final = "en"
BLOG_EDITOR_LANGUAGE_PATTERN: Final = r"^(pt|en)$"

BLOG_IMAGES_DIR_NAME: Final = "blog-images"
BLOG_IMAGE_PARTIAL_SUFFIX: Final = ".part"
BLOG_IMAGE_TYPES: Final[dict[str, tuple[int, bytes]]] = {
    "png": (0, b"\x89PNG\r\n\x1a\n"),
    "jpg": (0, b"\xff\xd8\xff"),
    "webp": (8, b"WEBP"),
}
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
BLOG_IMAGE_MODEL: Final = "gpt-image-2"
BLOG_IMAGE_CACHE_PUBLIC: Final = "public, max-age=3600, must-revalidate"
BLOG_IMAGE_CACHE_PRIVATE: Final = "private, no-store"
BLOG_IMAGE_CACHE_NOT_FOUND: Final = "no-store"
BLOG_IMAGE_GENERATIONS_KEY: Final = "blog_image_generations"

PROMPT_DOMAIN_BLOG: Final = "blog"
PROMPT_IMAGE: Final = "image_prompt"
PROMPT_TRANSLATE_SECTION: Final = "translate_section"
IMAGE_PROMPT_MAX_CHARS: Final = 2000
IMAGE_PROMPT_BODY_CHARS: Final = 600

PHASE_BLOG_SECTION_IMAGE: Final = "blog_section_image"
PHASE_BLOG_SECTION_REWRITE: Final = "blog_section_rewrite"
PHASE_BLOG_TRANSLATION: Final = "blog_translation"

VERSION_CONTENT_TYPE_BLOG_POST: Final = "blog_post"
VERSION_SUMMARY_SAVE: Final = "Before save"
VERSION_SUMMARY_RESTORE: Final = "Before restoring version {version_number}"
VERSION_SUMMARY_SLOT: Final = "Before {action}"
BLOG_VERSION_HISTORY_MAX: Final = 50

SUGGEST_KEY_TEXT: Final = "suggested_text"
SUGGEST_KEY_EXPLANATION: Final = "explanation"
CODE_FENCE: Final = "```"

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
ERR_BLOG_TRANSLATION_WRONG_LANGUAGE: Final = "blog_translation_wrong_language"
ERR_BLOG_SCHEDULE_NOT_SET: Final = "blog_schedule_not_set"
ERR_BLOG_VERSION_EMPTY: Final = "blog_version_empty"

REWRITE_NO_HEADING_INSTRUCTION: Final = (
    "Rewrite only the body of this section. Do not repeat the heading above as "
    "a title, a heading, a bold line or a plain line. Start directly with the "
    "body text and return only the body text."
)
