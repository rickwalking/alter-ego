"""Constants for the blog writer + image generation run (AE-0425, ADR-0025).

The run state lives in ``ai_generation_metadata.generation`` of the blog row:
``{status, kind, started_at, heartbeat_at, finished_at, lease_id, attempt,
errors, recoverable, request, warnings}``. Every write of the run is fenced on
``lease_id`` so a stale/duplicate task cannot clobber a newer attempt.
"""

from typing import Final

# --- ai_generation_metadata keys --------------------------------------------
GEN_KEY_STATUS: Final = "status"
GEN_KEY_KIND: Final = "kind"
GEN_KEY_STARTED_AT: Final = "started_at"
GEN_KEY_HEARTBEAT_AT: Final = "heartbeat_at"
GEN_KEY_FINISHED_AT: Final = "finished_at"
GEN_KEY_LEASE_ID: Final = "lease_id"
GEN_KEY_ATTEMPT: Final = "attempt"
GEN_KEY_ERRORS: Final = "errors"
GEN_KEY_RECOVERABLE: Final = "recoverable"
GEN_KEY_REQUEST: Final = "request"
GEN_KEY_WARNINGS: Final = "warnings"
GEN_KEY_IMAGE_COUNT: Final = "image_count"
# N + 1: the cover plus one image per section (the carousel slide count).
GEN_KEY_IMAGE_SLOTS: Final = "image_slots"
METADATA_KEY_VOICE_SCORE: Final = "voice_score"

# Error entry keys (``generation.errors[]``).
ERROR_KEY_CODE: Final = "code"
ERROR_KEY_SLOT: Final = "slot"
ERROR_KEY_REASON: Final = "reason"
ERROR_KEY_AT: Final = "at"

# --- statuses ---------------------------------------------------------------
GENERATION_STATUS_COMPLETE: Final = "complete"
GENERATION_STATUS_PARTIAL: Final = "partial"
GENERATION_STATUS_FAILED: Final = "failed"
# ``partial`` = the article exists but image slots are empty: its retry only
# fills those slots (images-only), it never rewrites the article.
GENERATION_STATUSES_RETRYABLE: Final[frozenset[str]] = frozenset({
    GENERATION_STATUS_FAILED,
    GENERATION_STATUS_PARTIAL,
})

# --- kinds (which entry point started the run) -------------------------------
GENERATION_KIND_FROM_CAROUSEL: Final = "from_carousel"
GENERATION_KIND_STANDALONE: Final = "standalone"
# A retry of a post that already has its article: only empty image slots run.
GENERATION_MODE_IMAGES_ONLY: Final = "images_only"
GEN_KEY_MODE: Final = "mode"

# --- request keys (stored so a retry re-runs the same request) ---------------
REQUEST_KEY_PROJECT_ID: Final = "project_id"
REQUEST_KEY_TOPIC: Final = "topic"
REQUEST_KEY_PERSONA_ID: Final = "persona_id"
REQUEST_KEY_LANGUAGE: Final = "language"
REQUEST_KEY_SOURCE_URLS: Final = "source_urls"

# --- error codes ------------------------------------------------------------
ERR_GENERATION_INTERRUPTED: Final = "generation_interrupted"
ERR_GENERATION_TIMEOUT: Final = "generation_timeout"
ERR_GENERATION_CANCELLED: Final = "generation_cancelled"
ERR_GENERATION_LLM_FAILED: Final = "generation_llm_failed"
ERR_GENERATION_CONFLICT: Final = "generation_conflict"
ERR_GENERATION_FAILED: Final = "generation_failed"
ERR_INVALID_GENERATED_DOCUMENT: Final = "invalid_generated_document"
ERR_SECTION_COUNT_MISMATCH: Final = "section_count_mismatch"
ERR_IMAGE_FAILED: Final = "image_failed"
ERR_IMAGE_COST_CAP: Final = "image_cost_cap_reached"
ERR_GENERATION_IN_PROGRESS: Final = "blog_generation_in_progress"
ERR_GENERATION_NOT_RETRYABLE: Final = "blog_generation_not_retryable"
ERR_BLOG_POST_EXISTS_FOR_PROJECT: Final = "blog_post_exists_for_project"

# --- warnings ---------------------------------------------------------------
# ADR-0013: a carousel-origin post is public only while its parent carousel is
# public, so a post generated from a private carousel would 404 once published.
WARNING_CAROUSEL_PRIVATE: Final = "carousel_private"

# --- image slots ------------------------------------------------------------
IMAGE_SLOT_COVER: Final = "cover"

# --- defaults (Settings) ----------------------------------------------------
DEFAULT_BLOG_IMAGE_CONCURRENCY: Final = 2
DEFAULT_BLOG_GENERATION_TIMEOUT_SECONDS: Final = 900
DEFAULT_BLOG_GENERATION_STALE_SECONDS: Final = 180
BLOG_GENERATION_HEARTBEAT_SECONDS: Final = 30.0
# The owner persona used when neither the request nor the project names one
# (the same fallback name as the autopilot, AE-0371).
BLOG_DEFAULT_PERSONA_NAME: Final = "Pedro"

# --- observability ----------------------------------------------------------
TRACE_CONTENT_TYPE_BLOG_POST: Final = "blog_post"
PHASE_BLOG_GENERATION: Final = "blog_generation"
AGENT_BLOG_WRITER: Final = "blog_writer"
AGENT_BLOG_VOICE_GATE: Final = "blog_voice_gate"
AGENT_BLOG_IMAGES: Final = "blog_images"
LOG_GENERATION_STARTED: Final = "blog_generation_started"
LOG_GENERATION_FINISHED: Final = "blog_generation_finished"
LOG_GENERATION_FAILED: Final = "blog_generation_failed"
LOG_GENERATION_LEASE_LOST: Final = "blog_generation_lease_lost"
LOG_GENERATION_REAPED: Final = "blog_generation_reaped"
LOG_IMAGE_FAILED: Final = "blog_image_failed"
LOG_IMAGES_DONE: Final = "blog_images_done"
# Version-history summary of the generation's own writes (AE-0424 slot path).
VERSION_SUMMARY_GENERATION: Final = "Before blog generation"
LOG_SOURCE_LEAK_STRIPPED: Final = "blog_source_leak_stripped"
LOG_HEARTBEAT_FAILED: Final = "blog_generation_heartbeat_failed"
LOG_ENGLISH_IN_PT: Final = "blog_english_in_pt_section"
TASK_NAME_PREFIX: Final = "blog-generation-"

# Section/count normalization.
LANGUAGE_PT: Final = "pt"
LANGUAGE_EN: Final = "en"
STANDALONE_SLUG_SUFFIX_CHARS: Final = 8
CAROUSEL_SLUG_PREFIX: Final = "carousel-"
BLOG_TITLE_MAX_CHARS: Final = 255
