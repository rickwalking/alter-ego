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
BLOG_IMAGE_EXTENSION: Final = ".jpg"
BLOG_IMAGES_ROUTE_PREFIX: Final = "/api/blog-images"
BLOG_IMAGE_FILENAME_PATTERN: Final = (
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jpg$"
)
BLOG_IMAGE_CACHE_CONTROL: Final = "public, max-age=31536000, immutable"
MEDIA_TYPE_JPEG: Final = "image/jpeg"

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
VERSION_SUMMARY_SAVE: Final = "Saved"
VERSION_SUMMARY_RESTORE: Final = "Restored from version {version_number}"

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
ERR_BLOG_PERSONA_REQUIRED: Final = "blog_persona_required"
ERR_BLOG_REWRITE_EMPTY: Final = "blog_rewrite_empty"
ERR_BLOG_TRANSLATION_FAILED: Final = "blog_translation_failed"
ERR_BLOG_SCHEDULE_NOT_SET: Final = "blog_schedule_not_set"
ERR_BLOG_REVIEWER_REQUIRED: Final = "blog_reviewer_required"
