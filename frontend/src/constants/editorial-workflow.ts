import { HTTP_STATUS } from "@/constants/api";

/** Maps editorial workflow phases to legacy pipeline phase keys for progress UI. */
export const EDITORIAL_TO_PIPELINE_PHASE: Record<string, string> = {
  research: "researching",
  outline: "drafting",
  content: "drafting",
  design: "designing",
  images: "generating_images",
  final_review: "exporting",
};

/** Editorial workflow SSE event names (must match backend SSE_EVENT_*). */
export const EDITORIAL_WORKFLOW_SSE_EVENTS = {
  PHASE_CHANGED: "phase_change",
  PROGRESS: "progress",
  REVIEW_REQUIRED: "review_required",
  ERROR: "error",
  ARTIFACT: "artifact",
  // AE-0315 run lifecycle (backend domain.constants.carousel_run).
  RUN_STARTED: "run.started",
  RUN_STAGE_CHANGED: "run.stage_changed",
  RUN_FINISHED: "run.finished",
} as const;

/** Coarse run stages emitted by the backend at stage boundaries (AE-0315). */
export const EDITORIAL_RUN_STAGES = {
  GENERATING: "generating",
  VALIDATING: "validating",
  PERSISTING: "persisting",
} as const;

export type EditorialRunStage =
  (typeof EDITORIAL_RUN_STAGES)[keyof typeof EDITORIAL_RUN_STAGES];

/**
 * AE-0315: past this elapsed time the in-progress banner offers "Check
 * again" (the backend reaper clears genuinely dead runs within a few
 * watchdog ticks; healthy runs observed in prod take ~13-15 min, so the
 * escape hatch appears well before that without ever blocking the run).
 */
export const EDITORIAL_RUN_CHECK_AGAIN_AFTER_MS = 5 * 60_000;

/** Editorial workflow phase identifiers (mirror backend PHASE_*). */
export const EDITORIAL_PHASES = {
  RESEARCH: "research",
  OUTLINE: "outline",
  CONTENT: "content",
  DESIGN: "design",
  IMAGES: "images",
  FINAL_REVIEW: "final_review",
  PUBLISHED: "published",
} as const;

/** Workflow state transport modes for UI observability. */
export const EDITORIAL_WORKFLOW_TRANSPORT_MODE = {
  SSE: "sse",
  POLLING_FALLBACK: "polling-fallback",
} as const;

export type EditorialWorkflowTransportMode =
  (typeof EDITORIAL_WORKFLOW_TRANSPORT_MODE)[keyof typeof EDITORIAL_WORKFLOW_TRANSPORT_MODE];

/** Polling backoff intervals (ms) when SSE is unavailable. */
export const EDITORIAL_WORKFLOW_POLL_BACKOFF_MS = [
  5_000, 10_000, 30_000,
] as const;

/** Resume polling while backend continues after proxy/client timeout. */
export const EDITORIAL_WORKFLOW_RESUME_POLL_INTERVAL_MS = 5_000;
export const EDITORIAL_WORKFLOW_RESUME_POLL_MAX_ATTEMPTS = 60;

/** HTTP statuses that indicate a definitive resume rejection (not transport timeout). */
export const EDITORIAL_WORKFLOW_RESUME_CLIENT_ERROR_STATUSES = [
  HTTP_STATUS.BAD_REQUEST,
  HTTP_STATUS.FORBIDDEN,
  HTTP_STATUS.CONFLICT,
  HTTP_STATUS.UNPROCESSABLE_ENTITY,
] as const;

/** Phases editors can send final review back to (CP-019). */
export const FINAL_REVIEW_SEND_BACK_PHASES = [
  EDITORIAL_PHASES.RESEARCH,
  EDITORIAL_PHASES.OUTLINE,
  EDITORIAL_PHASES.CONTENT,
  EDITORIAL_PHASES.DESIGN,
  EDITORIAL_PHASES.IMAGES,
] as const;

export type FinalReviewSendBackPhase =
  (typeof FINAL_REVIEW_SEND_BACK_PHASES)[number];

/** Final review tab identifiers. */
export const FINAL_REVIEW_TABS = {
  CAROUSEL: "carousel",
  BLOG: "blog",
  CAPTION: "caption",
  QUALITY: "quality",
} as const;

export type FinalReviewTab =
  (typeof FINAL_REVIEW_TABS)[keyof typeof FINAL_REVIEW_TABS];

/** Editorial workflow status values from backend. */
export const EDITORIAL_WORKFLOW_STATUS = {
  APPROVED_FOR_PUBLISH: "approved_for_publish",
} as const;

/** Minimum persona voice match score required before content approval. */
export const PERSONA_VOICE_MATCH_MIN_SCORE = 70;

/** Maps backend artifact SSE types to workflow state fields. */
export const WORKFLOW_ARTIFACT_FIELD_MAP: Record<string, string> = {
  outline: "outline",
  slide_drafts: "slide_drafts",
  slide_image_prompts: "slide_image_prompts",
  design_applied: "design_applied",
  image_assets: "image_assets",
  persona_scores: "persona_scores",
  localized_slides: "localized_slides",
  presentation_validation: "presentation_validation",
} as const;

/**
 * Machine-readable resume conflict codes surfaced in the 409 `detail`
 * (AE-0310; backend `rag_backend.domain.constants.carousel_conflicts`).
 */
export const EDITORIAL_WORKFLOW_CONFLICT_CODES = {
  REVISION_CAP_EXCEEDED: "revision_cap_exceeded",
  // AE-0315: run-in-progress resume conflict — renders the in-progress
  // banner (via a state refresh), never an error toast.
  RUN_IN_PROGRESS: "resume_already_in_progress",
  // AE-0315: stale lock_version — distinct copy from the other two causes.
  VERSION_CONFLICT: "version_conflict",
} as const;

/**
 * AE-0310: backend hint code carried in `design_recovery_hint` while the
 * design step holds a blocking presentation validation report.
 */
export const DESIGN_VALIDATION_RECOVERY_HINT =
  "design_validation_blocked_edit_or_send_back";
