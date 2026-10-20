/**
 * Blog section editor constants (AE-0424, ADR-0025).
 *
 * Error kinds the editor maps to copy, and the backend `detail` codes that
 * mean "this row is still legacy markdown" (the cutover has not reached it):
 * the editor then shows a blocking "migration pending" banner instead of
 * parsing or persisting the legacy shape itself (AC15).
 */

/** next-intl namespace of the editor's own copy (UI locale, not content). */
export const BLOG_EDITOR_I18N_NAMESPACE = "dashboard.blogPosts.editor";

export const BLOG_EDITOR_ERROR_KINDS = {
  VERSION_CONFLICT: "version_conflict",
  MIGRATION_PENDING: "migration_pending",
  VALIDATION: "validation",
  STATUS_GUARD: "status_guard",
  CONFLICT: "conflict",
  NOT_FOUND: "not_found",
  AI_FAILED: "ai_failed",
  /** 429: the per-post image budget (BLOG_IMAGE_COST_CAP) is used up. */
  BUDGET: "budget",
  FAILED: "failed",
} as const;

export type BlogEditorErrorKind =
  (typeof BLOG_EDITOR_ERROR_KINDS)[keyof typeof BLOG_EDITOR_ERROR_KINDS];

/** `InvalidBlogDocumentError` codes of a non-v2 stored row (backend 422). */
export const BLOG_MIGRATION_PENDING_CODES = [
  "blog_document_not_v2",
  "blog_document_not_object",
  "invalid_blog_document",
] as const;

/**
 * Backend `detail` codes with their own copy (AE-0438, F-11). The value is the
 * message key under `dashboard.blogPosts.editor.errors.code.<value>`; codes not
 * listed here fall back to the kind-level message (`errors.<kind>`).
 */
export const BLOG_EDITOR_ERROR_CODE_KEYS = {
  self_review_not_allowed: "self_review",
  blog_reviewer_required: "reviewer_required",
  blog_version_empty: "version_empty",
  blog_document_has_no_sections: "empty_document",
  blog_document_not_publishable: "not_publishable",
  blog_heading_invalid: "heading_invalid",
  blog_section_too_long: "section_too_long",
  blog_section_not_found: "section_not_found",
  blog_translation_exists: "translation_exists",
  blog_translation_failed: "translation_failed",
  blog_image_budget_exhausted: "budget",
  blog_image_persist_failed: "image_persist_failed",
  blog_image_generation_failed: "image_generation_failed",
  blog_persona_required: "persona_required",
  blog_rewrite_too_long: "rewrite_too_long",
  blog_rewrite_empty: "rewrite_empty",
  blog_image_alt_blank: "alt_blank",
  blog_schedule_not_set: "schedule_not_set",
} as const;

/** Write-time limits mirrored from `domain/constants/blog_document.py`. */
export const BLOG_HEADING_MAX_LENGTH = 200;
export const BLOG_SECTION_MAX_LENGTH = 20_000;
export const BLOG_IMAGE_TEXT_MAX_LENGTH = 500;
export const BLOG_IMAGE_PROMPT_MAX_LENGTH = 2_000;
export const BLOG_REJECT_REASON_MAX_LENGTH = 2_000;
export const BLOG_HEADING_MARKER = "#";

/** Voice score bar (ADR-0003): >= 70 before human review. */
export const BLOG_VOICE_SCORE_MIN = 70;
