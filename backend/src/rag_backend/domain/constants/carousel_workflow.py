"""Constants for the 7-phase carousel editorial workflow."""

PHASE_BRIEF = "brief"
PHASE_RESEARCH = "research"
PHASE_OUTLINE = "outline"
PHASE_CONTENT = "content"
PHASE_DESIGN = "design"
PHASE_IMAGES = "images"
PHASE_FINAL_REVIEW = "final_review"
PHASE_PUBLISHED = "published"
# Internal graph-only node (AE-0288): after final-review approval the graph holds
# here at an interrupt instead of reaching END, so the approved carousel stays
# resumable for a send-back. NOT a user-facing phase — never surfaced as
# ``current_phase`` (get_state keeps the phase as ``final_review`` while held).
PHASE_APPROVED_HOLD = "approved_hold"

PHASE_STATUS_PENDING = "pending"
PHASE_STATUS_IN_PROGRESS = "in_progress"
PHASE_STATUS_AWAITING_HUMAN = "awaiting_human"
PHASE_STATUS_APPROVED = "approved"
PHASE_STATUS_REJECTED = "rejected"
PHASE_STATUS_FAILED = "failed"

CAROUSEL_WORKFLOW_PHASES: tuple[str, ...] = (
    PHASE_BRIEF,
    PHASE_RESEARCH,
    PHASE_OUTLINE,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_IMAGES,
    PHASE_FINAL_REVIEW,
    PHASE_PUBLISHED,
)

INTERRUPT_TYPE_RESEARCH_REVIEW = "research_review"
INTERRUPT_TYPE_OUTLINE_REVIEW = "outline_review"
INTERRUPT_TYPE_CONTENT_REVIEW = "content_review"
INTERRUPT_TYPE_DESIGN_REVIEW = "design_review"
INTERRUPT_TYPE_IMAGE_REVIEW = "image_review"
INTERRUPT_TYPE_FINAL_REVIEW = "final_review"

REVIEW_ACTION_APPROVE = "approve"
REVIEW_ACTION_REJECT = "reject"
REVIEW_ACTION_REVISE = "revise"
REVIEW_ACTION_EDIT = "edit"

WORKFLOW_STATUS_APPROVED_FOR_PUBLISH = "approved_for_publish"

CAROUSEL_EDITORIAL_WORKFLOW_STATUS_DRAFT = "draft"

WORKFLOW_METADATA_EDITORIAL_7_PHASE = "editorial_7_phase"
WORKFLOW_TRACE_PHASE_HUMAN_REVIEW = "human_review"
WORKFLOW_TRACE_PHASE_REVIEW = "review"

DEFAULT_REVISION_CAP_PER_PHASE = 5
DEFAULT_PHASE_RETRY_CAP = 3

SOURCE_TYPE_DOCUMENT = "document"
SOURCE_TYPE_URL = "url"

ERR_REVISE_FEEDBACK_REQUIRED = "revise_feedback_required"
ERR_REVISION_CAP_EXCEEDED = "revision_cap_exceeded"
ERR_PERSONA_SCORE_TOO_LOW = "persona_score_too_low"
ERR_PRESENTATION_VALIDATION_BLOCKED = "presentation_validation_blocked"
ERR_WORKFLOW_NOT_APPROVED_FOR_PUBLISH = "workflow_not_approved_for_publish"
ERR_STRUCTURED_FEEDBACK_FINAL_REVIEW_ONLY = "structured_feedback_final_review_only"
# AE-0310: renamed from ERR_EDITED_SLIDES_CONTENT_ONLY when the allowlist widened
# to {content, design, final_review}. The wire value is renamed too: no client
# string-matches the old detail (the frontend surfaces `detail` verbatim and has
# no logic keyed on it), so keeping the stale "content_phase_only" wording would
# only mislead API consumers.
ERR_EDITED_SLIDES_PHASE_NOT_ALLOWED = "edited_localized_slides_phase_not_allowed"
ERR_SEND_BACK_TARGET_NOT_ALLOWED = "send_back_target_phase_not_allowed"
ERR_CAROUSEL_NOT_COMPLETED = "carousel_not_completed"
ERR_WORKFLOW_PHASE_FAILED = "workflow_phase_failed"
ERR_WORKFLOW_SSE_SUBSCRIBER_LIMIT = "workflow_sse_subscriber_limit_exceeded"
ERR_RESUME_ALREADY_IN_PROGRESS = "resume_already_in_progress"
ERR_BACKGROUND_RESUME_FAILED = "background_resume_failed"
ERR_BACKGROUND_RESUME_STUCK = "background_resume_stuck"
ERR_UNSUPPORTED_REVIEW_ACTION = "unsupported_review_action"

STRUCTURED_FEEDBACK_KEY = "structured_feedback"
STRUCTURED_FEEDBACK_TARGET_PHASE_KEY = "target_phase"
STRUCTURED_FEEDBACK_EDITED_TEXT_KEY = "edited_text"
STRUCTURED_FEEDBACK_EDITED_SLIDES_KEY = "edited_localized_slides"
SEND_BACK_TARGET_PHASE_KEY = "send_back_target_phase"
WORKFLOW_ERROR_KEY = "workflow_error"
PERSONA_SCORE_OVERALL_KEY = "overall"
SLIDE_DRAFT_TEXT_KEY = "draft_text"
WORKFLOW_STATE_LINKEDIN_POST_PT_KEY = "linkedin_post_pt"
WORKFLOW_STATE_LINKEDIN_POST_EN_KEY = "linkedin_post_en"

WORKFLOW_ARTIFACT_TYPE_OUTLINE = "outline"
WORKFLOW_ARTIFACT_TYPE_SLIDE_DRAFTS = "slide_drafts"
WORKFLOW_ARTIFACT_TYPE_DESIGN_APPLIED = "design_applied"
WORKFLOW_ARTIFACT_TYPE_IMAGE_ASSETS = "image_assets"
WORKFLOW_ARTIFACT_TYPE_PERSONA_SCORES = "persona_scores"
WORKFLOW_ARTIFACT_FIELD_TYPE = "artifact_type"
WORKFLOW_ARTIFACT_FIELD_DATA = "data"

FINAL_REVIEW_SEND_BACK_PHASES: frozenset[str] = frozenset({
    PHASE_RESEARCH,
    PHASE_OUTLINE,
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_IMAGES,
})

# AE-0310: phases whose review gate accepts ``edited_localized_slides``.
# Widened from content-only so a reviewer parked at design/final_review with
# content-level violations can fix copy in place (uniform semantics: apply
# edits, re-validate, store the fresh report).
EDITED_SLIDES_ALLOWED_PHASES: frozenset[str] = frozenset({
    PHASE_CONTENT,
    PHASE_DESIGN,
    PHASE_FINAL_REVIEW,
})

# AE-0310: phases a design revise may send the workflow back to.
DESIGN_SEND_BACK_PHASES: frozenset[str] = frozenset({PHASE_CONTENT})

# AE-0310: client-displayable hint code emitted with a still-blocking design
# re-interrupt — direct edits or a send-back resolve violations; a plain revise
# alone does not modify content. The frontend maps this code to i18n copy.
DESIGN_VALIDATION_RECOVERY_HINT = "design_validation_blocked_edit_or_send_back"

REVIEW_ACTIONS: tuple[str, ...] = (
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REJECT,
    REVIEW_ACTION_REVISE,
    REVIEW_ACTION_EDIT,
)

RESUME_ROUTE_SUPPORTED_ACTIONS: frozenset[str] = frozenset({
    REVIEW_ACTION_APPROVE,
    REVIEW_ACTION_REVISE,
})
