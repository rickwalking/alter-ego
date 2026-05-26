"""Constants for AI content disclosure labeling (QUAL-002)."""

AI_DISCLOSURE_NONE = "none"
AI_DISCLOSURE_ASSISTED = "ai_assisted"
AI_DISCLOSURE_GENERATED = "ai_generated"
AI_DISCLOSURE_HYBRID = "ai_human_hybrid"

AI_DISCLOSURE_LEVELS = (
    AI_DISCLOSURE_NONE,
    AI_DISCLOSURE_ASSISTED,
    AI_DISCLOSURE_GENERATED,
    AI_DISCLOSURE_HYBRID,
)

AI_ACTION_SUGGEST = "ai_suggest"
AI_ACTION_IMPROVE = "ai_improve"
AI_ACTION_GENERATE_IMAGE = "ai_generate_image"

ERR_DISCLOSURE_REQUIRED = (
    "AI disclosure label is required before publishing AI-assisted content"
)

__all__ = [
    "AI_ACTION_GENERATE_IMAGE",
    "AI_ACTION_IMPROVE",
    "AI_ACTION_SUGGEST",
    "AI_DISCLOSURE_ASSISTED",
    "AI_DISCLOSURE_GENERATED",
    "AI_DISCLOSURE_HYBRID",
    "AI_DISCLOSURE_LEVELS",
    "AI_DISCLOSURE_NONE",
    "ERR_DISCLOSURE_REQUIRED",
]
