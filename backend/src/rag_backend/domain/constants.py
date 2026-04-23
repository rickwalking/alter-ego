"""Domain-level constants."""

# Document statuses
STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# Valid document statuses
VALID_STATUSES = {STATUS_PENDING, STATUS_PROCESSING, STATUS_COMPLETED, STATUS_FAILED}

# Message roles
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_SYSTEM = "system"

# Valid message roles
VALID_ROLES = {ROLE_USER, ROLE_ASSISTANT, ROLE_SYSTEM}

# =============================================================================
# Carousel Pipeline Constants
# =============================================================================

# Carousel statuses
CAROUSEL_STATUS_PENDING = "pending"
CAROUSEL_STATUS_RESEARCHING = "researching"
CAROUSEL_STATUS_DRAFTING = "drafting"
CAROUSEL_STATUS_DESIGNING = "designing"
CAROUSEL_STATUS_GENERATING_IMAGES = "generating_images"
CAROUSEL_STATUS_EXPORTING = "exporting"
CAROUSEL_STATUS_COMPLETED = "completed"
CAROUSEL_STATUS_FAILED = "failed"

# Valid carousel statuses
VALID_CAROUSEL_STATUSES = {
    CAROUSEL_STATUS_PENDING,
    CAROUSEL_STATUS_RESEARCHING,
    CAROUSEL_STATUS_DRAFTING,
    CAROUSEL_STATUS_DESIGNING,
    CAROUSEL_STATUS_GENERATING_IMAGES,
    CAROUSEL_STATUS_EXPORTING,
    CAROUSEL_STATUS_COMPLETED,
    CAROUSEL_STATUS_FAILED,
}

# Slide types
SLIDE_TYPE_INTRO = "intro"
SLIDE_TYPE_CONTENT = "content"
SLIDE_TYPE_CLOSING = "closing"
SLIDE_TYPE_CTA = "cta"

# Default aspect ratio
CAROUSEL_ASPECT_RATIO = "1080x1350"
CAROUSEL_WIDTH = 1080
CAROUSEL_HEIGHT = 1350

# Default language
CAROUSEL_DEFAULT_LANGUAGE = "pt-BR"

# Default slides config
CAROUSEL_DEFAULT_SLIDES_CONFIG = "1 intro, 3 content, 1 closing, 1 cta"

# Theme color palettes
CAROUSEL_THEMES: dict[str, dict[str, str]] = {
    "cybersecurity": {
        "primary": "#ef4444",
        "accent": "#00d4ff",
        "background": "#0a0e17",
    },
    "ai_competition": {
        "primary": "#3b82f6",
        "accent": "#f59e0b",
        "background": "#0a0e17",
    },
    "developer_skills": {
        "primary": "#0ac5a8",
        "accent": "#8b5cf6",
        "background": "#080c12",
    },
    "source_code": {
        "primary": "#a855f7",
        "accent": "#f97316",
        "background": "#0c0a14",
    },
    "social_engineering": {
        "primary": "#f59e0b",
        "accent": "#ef4444",
        "background": "#0a0c14",
    },
}

# Research source types
RESEARCH_SOURCE_TWITTER = "twitter"
RESEARCH_SOURCE_BLOG = "blog"
RESEARCH_SOURCE_REDDIT = "reddit"
RESEARCH_SOURCE_GITHUB = "github"
RESEARCH_SOURCE_NEWS = "news"
RESEARCH_SOURCE_DOCUMENTATION = "documentation"

VALID_RESEARCH_SOURCE_TYPES = {
    RESEARCH_SOURCE_TWITTER,
    RESEARCH_SOURCE_BLOG,
    RESEARCH_SOURCE_REDDIT,
    RESEARCH_SOURCE_GITHUB,
    RESEARCH_SOURCE_NEWS,
    RESEARCH_SOURCE_DOCUMENTATION,
}

# Image generation providers (the concrete model behind the service).
IMAGE_MODEL_GEMINI = "gemini"
IMAGE_MODEL_OPENAI = "openai"

VALID_IMAGE_MODELS: set[str] = {IMAGE_MODEL_GEMINI, IMAGE_MODEL_OPENAI}

# Image style presets (wrap the LLM scene with provider-tuned directives).
IMAGE_STYLE_COMIC_NEON = "comic_neon"
IMAGE_STYLE_CINEMATIC = "cinematic"
IMAGE_STYLE_HYPERREAL = "hyperreal"
IMAGE_STYLE_NEO_ANIME = "neo_anime"

VALID_IMAGE_STYLES: set[str] = {
    IMAGE_STYLE_COMIC_NEON,
    IMAGE_STYLE_CINEMATIC,
    IMAGE_STYLE_HYPERREAL,
    IMAGE_STYLE_NEO_ANIME,
}

# Design override key stored in project.extras for refine_carousel_design.
DESIGN_OVERRIDES_KEY = "design_overrides"

# Default combo applied when a caller omits the fields (back-compat
# with every carousel created before pluggable providers landed).
IMAGE_MODEL_DEFAULT = IMAGE_MODEL_GEMINI
IMAGE_STYLE_DEFAULT = IMAGE_STYLE_COMIC_NEON

# Only these (model, style) tuples are wired in the registry. Anything
# else fails API validation with a 422 before the pipeline runs.
SUPPORTED_IMAGE_COMBOS: set[tuple[str, str]] = {
    (IMAGE_MODEL_GEMINI, IMAGE_STYLE_COMIC_NEON),
    (IMAGE_MODEL_OPENAI, IMAGE_STYLE_CINEMATIC),
    (IMAGE_MODEL_OPENAI, IMAGE_STYLE_HYPERREAL),
    (IMAGE_MODEL_OPENAI, IMAGE_STYLE_NEO_ANIME),
}
