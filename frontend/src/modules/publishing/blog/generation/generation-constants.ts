/**
 * Blog generation run constants (AE-0425, ADR-0025).
 *
 * Mirrors `ai_generation_metadata.generation` written by the backend
 * (`domain/constants/blog_generation.py`): the run status, the warnings and
 * the error codes the editor surfaces.
 */

export const GENERATION_STATUS = {
  IN_PROGRESS: "in_progress",
  COMPLETE: "complete",
  PARTIAL: "partial",
  FAILED: "failed",
} as const;

export type GenerationStatus =
  (typeof GENERATION_STATUS)[keyof typeof GENERATION_STATUS];

/** ADR-0013: a post from a private carousel 404s publicly once published. */
export const GENERATION_WARNING_CAROUSEL_PRIVATE = "carousel_private";

/** The run was killed by a deploy/restart and reaped (owner retries). */
export const ERR_GENERATION_INTERRUPTED = "generation_interrupted";

/** 409 body code of `from-carousel` when the project already has a post. */
export const ERR_BLOG_POST_EXISTS_FOR_PROJECT = "blog_post_exists_for_project";

/** How often the editor re-reads a post while its generation runs (ms). */
export const GENERATION_POLL_INTERVAL_MS = 5000;

export const GENERATION_METADATA_KEY = "generation";

/** Standalone topic bounds (backend `BlogGenerateRequest`). */
export const GENERATION_TOPIC_MIN_CHARS = 3;
export const GENERATION_TOPIC_MAX_CHARS = 500;
