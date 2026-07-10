"""Field-name constants for the editorial workflow state dictionary.

These name the keys used in the raw workflow state mapping and the API
response payloads built from it. Centralizing them removes magic strings
from the editorial workflow route response builder.
"""

# Core workflow state fields
STATE_FIELD_PROJECT_ID = "project_id"
STATE_FIELD_CURRENT_PHASE = "current_phase"
STATE_FIELD_PHASE_STATUS = "phase_status"
STATE_FIELD_RESEARCH_FINDINGS = "research_findings"
STATE_FIELD_OUTLINE = "outline"
STATE_FIELD_SLIDE_DRAFTS = "slide_drafts"
STATE_FIELD_IMAGE_ASSETS = "image_assets"
STATE_FIELD_DESIGN_APPLIED = "design_applied"
STATE_FIELD_PHASE_PROGRESS = "phase_progress"
STATE_FIELD_STATUS = "status"
STATE_FIELD_WORKFLOW_STATUS = "workflow_status"
STATE_FIELD_CAPTION = "caption"
STATE_FIELD_BLOG_MARKDOWN = "blog_markdown"
STATE_FIELD_LINKEDIN_POST_PT = "linkedin_post_pt"
STATE_FIELD_LINKEDIN_POST_EN = "linkedin_post_en"
STATE_FIELD_PERSONA_SCORES = "persona_scores"
STATE_FIELD_RUBRIC_SCORES = "rubric_scores"
STATE_FIELD_PHASE_FEEDBACK = "phase_feedback"
STATE_FIELD_REVISION_COUNT = "revision_count"
STATE_FIELD_PRESENTATION_POLICY_VERSION = "presentation_policy_version"
STATE_FIELD_LOCALIZED_SLIDES = "localized_slides"
STATE_FIELD_PRESENTATION_VALIDATION = "presentation_validation"
# AE-0309: fail-closed content-gate validation report. Set (non-empty) only when
# the content build's validate -> repair -> retry chain still ends blocking; the
# content interrupt payload mirrors it so the reviewer sees the violations.
STATE_FIELD_CONTENT_GATE_VALIDATION = "content_gate_validation"
# AE-0310: hint code stored by the design ensure when the fresh presentation
# validation report still blocks (cleared to "" once validation passes).
STATE_FIELD_DESIGN_RECOVERY_HINT = "design_recovery_hint"
STATE_FIELD_LOCK_VERSION = "lock_version"
# Response field carrying the persisted failure message (AE-0009). The raw
# state stores the message under ``workflow_error`` (WORKFLOW_ERROR_KEY); this
# names the additive, optional response field surfaced to clients.
STATE_FIELD_ERROR_MESSAGE = "error_message"
STATE_FIELD_WORKFLOW_ERROR = "workflow_error"

STATE_DEFAULT_STATUS = "draft"

# Localized slide review fields
STATE_FIELD_SLIDE_INDEX = "slide_index"
STATE_FIELD_SLIDE_TYPE = "slide_type"
STATE_FIELD_PRESENTATION_PT = "presentation_pt"
STATE_FIELD_PRESENTATION_EN = "presentation_en"

# Validation report fields
STATE_FIELD_VALIDATION_STATUS = "validation_status"
STATE_FIELD_VALIDATED_AT = "validated_at"
STATE_FIELD_BLOCKING = "blocking"
STATE_FIELD_VIOLATIONS = "violations"

# Validation violation fields
STATE_FIELD_VIOLATION_CODE = "code"
STATE_FIELD_VIOLATION_MESSAGE = "message"
STATE_FIELD_VIOLATION_LOCALE = "locale"
STATE_FIELD_VIOLATION_FIELD = "field"

__all__ = [
    "STATE_DEFAULT_STATUS",
    "STATE_FIELD_BLOCKING",
    "STATE_FIELD_BLOG_MARKDOWN",
    "STATE_FIELD_CAPTION",
    "STATE_FIELD_CONTENT_GATE_VALIDATION",
    "STATE_FIELD_CURRENT_PHASE",
    "STATE_FIELD_DESIGN_APPLIED",
    "STATE_FIELD_DESIGN_RECOVERY_HINT",
    "STATE_FIELD_ERROR_MESSAGE",
    "STATE_FIELD_IMAGE_ASSETS",
    "STATE_FIELD_LINKEDIN_POST_EN",
    "STATE_FIELD_LINKEDIN_POST_PT",
    "STATE_FIELD_LOCALIZED_SLIDES",
    "STATE_FIELD_LOCK_VERSION",
    "STATE_FIELD_OUTLINE",
    "STATE_FIELD_PERSONA_SCORES",
    "STATE_FIELD_PHASE_FEEDBACK",
    "STATE_FIELD_PHASE_PROGRESS",
    "STATE_FIELD_PHASE_STATUS",
    "STATE_FIELD_PRESENTATION_EN",
    "STATE_FIELD_PRESENTATION_POLICY_VERSION",
    "STATE_FIELD_PRESENTATION_PT",
    "STATE_FIELD_PRESENTATION_VALIDATION",
    "STATE_FIELD_PROJECT_ID",
    "STATE_FIELD_RESEARCH_FINDINGS",
    "STATE_FIELD_REVISION_COUNT",
    "STATE_FIELD_RUBRIC_SCORES",
    "STATE_FIELD_SLIDE_DRAFTS",
    "STATE_FIELD_SLIDE_INDEX",
    "STATE_FIELD_SLIDE_TYPE",
    "STATE_FIELD_STATUS",
    "STATE_FIELD_VALIDATED_AT",
    "STATE_FIELD_VALIDATION_STATUS",
    "STATE_FIELD_VIOLATIONS",
    "STATE_FIELD_VIOLATION_CODE",
    "STATE_FIELD_VIOLATION_FIELD",
    "STATE_FIELD_VIOLATION_LOCALE",
    "STATE_FIELD_VIOLATION_MESSAGE",
    "STATE_FIELD_WORKFLOW_ERROR",
    "STATE_FIELD_WORKFLOW_STATUS",
]
