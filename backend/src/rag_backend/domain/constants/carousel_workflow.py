"""Constants for the 7-phase carousel editorial workflow."""

PHASE_BRIEF = "brief"
PHASE_RESEARCH = "research"
PHASE_OUTLINE = "outline"
PHASE_CONTENT = "content"
PHASE_DESIGN = "design"
PHASE_IMAGES = "images"
PHASE_FINAL_REVIEW = "final_review"
PHASE_PUBLISHED = "published"

PHASE_STATUS_PENDING = "pending"
PHASE_STATUS_IN_PROGRESS = "in_progress"
PHASE_STATUS_AWAITING_HUMAN = "awaiting_human"
PHASE_STATUS_APPROVED = "approved"
PHASE_STATUS_REJECTED = "rejected"

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
REVIEW_ACTION_EDIT = "edit"
