import { HTTP_STATUS } from "@/constants/api";

/** Editorial workflow SSE event names (must match backend SSE_EVENT_*). */
export const EDITORIAL_WORKFLOW_SSE_EVENTS = {
  PHASE_CHANGED: "phase_change",
  PROGRESS: "progress",
  REVIEW_REQUIRED: "review_required",
  ERROR: "error",
  ARTIFACT: "artifact",
  /** Run lifecycle events (backend ``domain.constants.carousel_run``). */
  RUN_STARTED: "run.started",
  RUN_STAGE_CHANGED: "run.stage_changed",
  RUN_FINISHED: "run.finished",
} as const;

/** Coarse run stages emitted by the backend at stage boundaries. */
export const EDITORIAL_RUN_STAGES = {
  GENERATING: "generating",
  VALIDATING: "validating",
  PERSISTING: "persisting",
} as const;

export type EditorialRunStage =
  (typeof EDITORIAL_RUN_STAGES)[keyof typeof EDITORIAL_RUN_STAGES];

/**
 * Past this elapsed time the in-progress banner offers "Check
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

/**
 * The image node stamps ``phase_progress.phase`` with the legacy
 * carousel status (``generating_images``), not the editorial phase it belongs
 * to. Tags not listed here are already editorial phase names.
 */
export const PHASE_PROGRESS_TAG_TO_EDITORIAL_PHASE: Readonly<
  Record<string, string>
> = {
  generating_images: EDITORIAL_PHASES.IMAGES,
};

/** Workflow state transport modes for UI observability. */
export const EDITORIAL_WORKFLOW_TRANSPORT_MODE = {
  SSE: "sse",
  POLLING_FALLBACK: "polling-fallback",
  /** Reconnects gave up (budget spent, workflow gone or auth lost). */
  DISCONNECTED: "disconnected",
} as const;

export type EditorialWorkflowTransportMode =
  (typeof EDITORIAL_WORKFLOW_TRANSPORT_MODE)[keyof typeof EDITORIAL_WORKFLOW_TRANSPORT_MODE];

/** Polling backoff intervals (ms) when SSE is unavailable. */
export const EDITORIAL_WORKFLOW_POLL_BACKOFF_MS = [
  5_000, 10_000, 30_000,
] as const;

/**
 * Stream reconnects walk the backoff array above (last delay reused)
 * and give up after this many attempts in a row; the editor then shows a
 * visible "live updates disconnected" state with a retry button.
 */
export const EDITORIAL_WORKFLOW_SSE_MAX_RECONNECT_ATTEMPTS = 5;

/**
 * EventSource cannot see the HTTP status of a failed stream, so a
 * stream error is followed by a GET workflow/state probe through the api-client
 * (whose 401 path is the session-expired redirect). The probe's verdict:
 * OK (state refetched, reconnect), AUTH_FAILED (redirected, never reconnect),
 * GONE (no workflow, stop) or TRANSIENT (backend unreachable, back off).
 */
export const WORKFLOW_STREAM_PROBE_OUTCOME = {
  OK: "ok",
  AUTH_FAILED: "auth_failed",
  GONE: "gone",
  TRANSIENT: "transient",
} as const;

export type WorkflowStreamProbeOutcome =
  (typeof WORKFLOW_STREAM_PROBE_OUTCOME)[keyof typeof WORKFLOW_STREAM_PROBE_OUTCOME];

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
 * (backend `rag_backend.domain.constants.carousel_conflicts`).
 */
export const EDITORIAL_WORKFLOW_CONFLICT_CODES = {
  REVISION_CAP_EXCEEDED: "revision_cap_exceeded",
  /** Run in progress: renders the in-progress banner (via a state refresh), never an error toast. */
  RUN_IN_PROGRESS: "resume_already_in_progress",
  /** Stale ``lock_version``: distinct copy from the other two causes. */
  VERSION_CONFLICT: "version_conflict",
} as const;

/**
 * Machine-readable 4xx ``detail`` codes of
 * ``POST /workflow/resume`` that get a translated message
 * (``editorialWorkflow.errors.resumeCodes.<code>``) instead of the raw code.
 */
export const EDITORIAL_RESUME_ERROR_CODES: ReadonlySet<string> = new Set([
  "edited_localized_slides_phase_not_allowed",
  "structured_feedback_final_review_only",
  "send_back_target_phase_not_allowed",
  "revise_feedback_required",
  "persona_score_too_low",
  "presentation_validation_blocked",
  "unsupported_review_action",
  "not_assigned_reviewer",
  "persona_not_found",
]);

/**
 * Backend hint code carried in `design_recovery_hint` while the
 * design step holds a blocking presentation validation report.
 */
export const DESIGN_VALIDATION_RECOVERY_HINT =
  "design_validation_blocked_edit_or_send_back";

/**
 * The structured item list each slide type renders (mirrors the
 * backend gate: a summary needs ``summary_points``, a closing slide needs 3
 * ``actions``, a content slide may carry ``features``). The editor offers this
 * list even when it is empty, so a missing list can be filled by hand.
 */
export const SLIDE_TYPE_ITEM_LIST_KEY: Readonly<Record<string, string>> = {
  summary: "summary_points",
  closing: "actions",
  content: "features",
};

/** Most items a structured list holds (features allow 2-4). */
export const STRUCTURED_LIST_MAX_ITEMS = 4;

/** Icons a new item takes by position (Lucide contract allowlist). */
export const STRUCTURED_ITEM_DEFAULT_ICONS = [
  "target",
  "wrench",
  "book-open",
  "shield-check",
] as const;
