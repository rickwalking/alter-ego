"""Constants for the blog writer + image generation run (ADR-0025).

The run state lives in ``ai_generation_metadata.generation`` of the blog row:
``{status, kind, started_at, heartbeat_at, finished_at, lease_id, attempt,
errors, recoverable, request, warnings}``. Every write of the run is fenced on
``lease_id`` so a stale/duplicate task cannot clobber a newer attempt.

Image slots are N + 1: the cover plus one image per section. A ``partial`` run has its
article but empty image slots, and its retry fills only those slots (images-only), never
rewriting the article. The request is stored so a retry re-runs the same request.
``image_timeout`` marks a slot still running when the images budget ran out;
``en_translation_wrong_language`` means the EN still read as Portuguese after the
bounded retranslations, so the article is stored without ``translations.en``. A
carousel-origin post is public only while its parent carousel is, so a post generated
from a private carousel gets the ``carousel_private`` warning. Stage budgets come from
production runs: the text stage (writer, both gates, EN repair) took 37 s to 3 min,
worst 14.7 min under model-queue contention, hence 30 min; images took 135-224 s per
concurrency wave, hence 360 s per wave times ceil(slots / concurrency). The default
persona is the owner's, the same fallback name as the autopilot.
"""

from typing import Final

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
GEN_KEY_IMAGE_SLOTS: Final = "image_slots"
METADATA_KEY_VOICE_SCORE: Final = "voice_score"

TRACE_INPUT_POST_ID: Final = "post_id"
TRACE_INPUT_TITLE: Final = "title"
TRACE_INPUT_SECTION_COUNT: Final = "section_count"
TRACE_INPUT_SLOT: Final = "slot"
TRACE_INPUT_SECTION_HEADING: Final = "section_heading"
TRACE_OUTPUT_SECTION_COUNT: Final = "section_count"
TRACE_OUTPUT_VOICE_SCORE: Final = "voice_score"
TRACE_OUTPUT_IMAGE_URL: Final = "image_url"
TRACE_OUTPUT_ERROR_CODE: Final = "error_code"

ERROR_KEY_CODE: Final = "code"
ERROR_KEY_SLOT: Final = "slot"
ERROR_KEY_REASON: Final = "reason"
ERROR_KEY_AT: Final = "at"

GENERATION_STATUS_COMPLETE: Final = "complete"
GENERATION_STATUS_PARTIAL: Final = "partial"
GENERATION_STATUS_FAILED: Final = "failed"
GENERATION_STATUSES_RETRYABLE: Final[frozenset[str]] = frozenset({
    GENERATION_STATUS_FAILED,
    GENERATION_STATUS_PARTIAL,
})

GENERATION_KIND_FROM_CAROUSEL: Final = "from_carousel"
GENERATION_KIND_STANDALONE: Final = "standalone"
GENERATION_MODE_IMAGES_ONLY: Final = "images_only"
GEN_KEY_MODE: Final = "mode"

REQUEST_KEY_PROJECT_ID: Final = "project_id"
REQUEST_KEY_TOPIC: Final = "topic"
REQUEST_KEY_PERSONA_ID: Final = "persona_id"
REQUEST_KEY_LANGUAGE: Final = "language"
REQUEST_KEY_SOURCE_URLS: Final = "source_urls"

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
ERR_IMAGE_TIMEOUT: Final = "image_timeout"
ERR_EN_WRONG_LANGUAGE: Final = "en_translation_wrong_language"
ERR_GENERATION_IN_PROGRESS: Final = "blog_generation_in_progress"
ERR_GENERATION_NOT_RETRYABLE: Final = "blog_generation_not_retryable"
ERR_BLOG_POST_EXISTS_FOR_PROJECT: Final = "blog_post_exists_for_project"

WARNING_CAROUSEL_PRIVATE: Final = "carousel_private"

IMAGE_SLOT_COVER: Final = "cover"

DEFAULT_BLOG_IMAGE_CONCURRENCY: Final = 2
DEFAULT_BLOG_GENERATION_TEXT_TIMEOUT_SECONDS: Final = 1800
DEFAULT_BLOG_IMAGE_WAVE_TIMEOUT_SECONDS: Final = 360
BLOG_EN_MAX_RETRANSLATIONS: Final = 2
DEFAULT_BLOG_GENERATION_STALE_SECONDS: Final = 180
BLOG_GENERATION_HEARTBEAT_SECONDS: Final = 30.0
BLOG_DEFAULT_PERSONA_NAME: Final = "Pedro"

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
LOG_IMAGES_TIMED_OUT: Final = "blog_images_timed_out"
LOG_EN_WRONG_LANGUAGE: Final = "blog_en_wrong_language"
LOG_EN_RETRANSLATION_FAILED: Final = "blog_en_retranslation_failed"
LOG_EN_REWRITE_DISCARDED: Final = "blog_en_rewrite_language_switch_discarded"
VERSION_SUMMARY_GENERATION: Final = "Before blog generation"
LOG_SOURCE_LEAK_STRIPPED: Final = "blog_source_leak_stripped"
LOG_HEARTBEAT_FAILED: Final = "blog_generation_heartbeat_failed"
LOG_ENGLISH_IN_PT: Final = "blog_english_in_pt_section"
TASK_NAME_PREFIX: Final = "blog-generation-"

LANGUAGE_PT: Final = "pt"
LANGUAGE_EN: Final = "en"
STANDALONE_SLUG_SUFFIX_CHARS: Final = 8
CAROUSEL_SLUG_PREFIX: Final = "carousel-"
BLOG_TITLE_MAX_CHARS: Final = 255
