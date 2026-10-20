"""Constants for the blog post document model (``blog.v2``, AE-0423, ADR-0025)."""

from typing import Final

# Schema marker of the only persisted ``blog_posts.content`` shape.
BLOG_SCHEMA_V2: Final = "blog.v2"

# Write-time ceiling for one section body. The cutover never truncates: an
# oversized migrated section is reported for the AE-0426 rebuild instead.
BLOG_SECTION_MAX_CHARS: Final = 20_000
BLOG_HEADING_MAX_CHARS: Final = 200

# Section ids are ``sec_<uuid4>``; the editor may mint its own ids with the
# same prefix, so the pattern accepts any short slug after it.
BLOG_SECTION_ID_PREFIX: Final = "sec_"
BLOG_SECTION_ID_PATTERN: Final = r"^sec_[A-Za-z0-9_-]{1,64}$"
BLOG_LANGUAGE_PATTERN: Final = r"^[a-z]{2}$"

BLOG_IMAGE_SOURCE_GENERATED: Final = "generated"
BLOG_HTTPS_SCHEME_PREFIX: Final = "https://"
BLOG_SAME_ORIGIN_PATH_PREFIX: Final = "/"
BLOG_PROTOCOL_RELATIVE_PREFIX: Final = "//"
BLOG_HEADING_MARKER: Final = "#"

# Document keys (shared by the parser, the projection and the cutover).
KEY_SCHEMA: Final = "schema"
KEY_COVER: Final = "cover"
KEY_SECTIONS: Final = "sections"
KEY_TRANSLATIONS: Final = "translations"
KEY_QUALITY: Final = "quality"
KEY_ID: Final = "id"
KEY_HEADING: Final = "heading"
KEY_BODY_MD: Final = "body_md"
KEY_IMAGE: Final = "image"
KEY_URL: Final = "url"
KEY_ALT: Final = "alt"
KEY_CAPTION: Final = "caption"
KEY_SOURCE: Final = "source"
KEY_CREATED_AT: Final = "created_at"

# Legacy (v1) content keys, read only by the one-shot cutover command.
LEGACY_KEY_MARKDOWN: Final = "markdown"
LEGACY_KEY_BODY: Final = "body"

# ``ai_generation_metadata.generation.status`` value that allows zero sections.
GENERATION_KEY: Final = "generation"
GENERATION_STATUS_KEY: Final = "status"
GENERATION_STATUS_IN_PROGRESS: Final = "in_progress"

# Error codes (API ``detail``).
ERR_INVALID_BLOG_DOCUMENT: Final = "invalid_blog_document"
ERR_BLOG_DOCUMENT_NOT_V2: Final = "blog_document_not_v2"
ERR_BLOG_DOCUMENT_NOT_OBJECT: Final = "blog_document_not_object"
ERR_BLOG_DUPLICATE_SECTION_ID: Final = "blog_duplicate_section_id"
ERR_BLOG_NO_SECTIONS: Final = "blog_document_has_no_sections"
ERR_BLOG_SECTION_TOO_LONG: Final = "blog_section_too_long"
ERR_BLOG_HEADING_INVALID: Final = "blog_heading_invalid"
ERR_BLOG_IMAGE_URL_INVALID: Final = "blog_image_url_invalid"
ERR_BLOG_IMAGE_ALT_BLANK: Final = "blog_image_alt_blank"
ERR_BLOG_TRANSLATION_LANGUAGE_INVALID: Final = "blog_translation_language_invalid"
ERR_BLOG_NOT_PUBLISHABLE: Final = "blog_document_not_publishable"
# Cutover bookkeeping (AE-0423). A cleared ``featured_image_url`` is stashed in
# ``ai_generation_metadata`` (never public) so ``--rollback`` can restore it.
CUTOVER_METADATA_KEY: Final = "blog_v2_cutover"
CUTOVER_STASH_FEATURED_KEY: Final = "featured_image_url"
VERSION_SNAPSHOT_KEY: Final = "snapshot"
