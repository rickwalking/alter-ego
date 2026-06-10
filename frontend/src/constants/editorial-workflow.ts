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
} as const;

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
  400, 403, 409, 422,
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
