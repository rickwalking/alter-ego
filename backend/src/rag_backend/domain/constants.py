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

# =============================================================================
# Brand-Aware Theme Resolution
# =============================================================================

# Brand color palettes extracted from real-world examples and corporate
# identity guidelines. When the carousel topic matches a brand, the
# pipeline uses these colors instead of the generic category themes.
# This reproduces the creative behavior of the original carousel skill
# (e.g., orange for Anthropic/Claude, blue for Google/Gemma).
BRAND_PALETTES: dict[str, dict[str, str]] = {
    "anthropic": {
        "primary": "#ea580c",
        "accent": "#22d3ee",
        "background": "#0a0b12",
    },
    "google": {
        "primary": "#3b82f6",
        "accent": "#f59e0b",
        "background": "#0a0e17",
    },
    "openai": {
        "primary": "#10a37f",
        "accent": "#f59e0b",
        "background": "#0a0e17",
    },
    "meta": {
        "primary": "#8b5cf6",
        "accent": "#0ac5a8",
        "background": "#0c0a14",
    },
    "microsoft": {
        "primary": "#0078d4",
        "accent": "#f59e0b",
        "background": "#0a0e17",
    },
}

# Keywords that trigger brand detection. Each brand maps to a list of
# lower-case tokens that strongly indicate the carousel is about that
# company or product line. The resolver scores matches and picks the
# highest-scoring brand.
BRAND_KEYWORDS: dict[str, list[str]] = {
    "anthropic": [
        "anthropic",
        "claude",
        "claude code",
        "opus",
        "sonnet",
        "haiku",
        "mcp",
        "computer use",
        "dario amodei",
        "daniela amodei",
    ],
    "google": [
        "google",
        "gemma",
        "gemini",
        "deepmind",
        "alphabet",
        "bard",
        "palm",
        "tensor",
        "tpu",
        "android",
    ],
    "openai": [
        "openai",
        "chatgpt",
        "gpt",
        "gpt-4",
        "gpt-5",
        "gpt-3",
        "gpt4",
        "gpt5",
        "gpt-4o",
        "gpt-4.5",
        "gpt-5.5",
        "dall-e",
        "sora",
        "o1",
        "o3",
        "sam altman",
        "greg brockman",
    ],
    "meta": [
        "meta",
        "facebook",
        "llama",
        "llama-2",
        "llama-3",
        "llama2",
        "llama3",
        "pytorch",
        "zuckerberg",
        "instagram",
        "whatsapp",
    ],
    "microsoft": [
        "microsoft",
        "azure",
        "copilot",
        "github copilot",
        "bing",
        "satya nadella",
        "windows",
        "xbox",
        "vs code",
        "visual studio",
    ],
}

# Category keywords used when no brand is detected. Maps the five
# predefined theme names to topic keywords that indicate the content
# belongs to that category.
THEME_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "cybersecurity": [
        "security",
        "attack",
        "vulnerability",
        "exploit",
        "breach",
        "hack",
        "zero-day",
        "zero day",
        "cve",
        "malware",
        "ransomware",
        "phishing",
        "pentest",
        "penetration",
        "backdoor",
        "trojan",
        "worm",
        "firewall",
        "cryptography",
        "encryption",
        "tls",
        "ssl",
        "oauth",
        "injection",
        "xss",
        "csrf",
        "sqli",
        "reverse shell",
        "rootkit",
        "ddos",
        "botnet",
        "apt",
        "threat",
        "incident response",
        "forensics",
        "blue team",
        "red team",
        "purple team",
        "soc",
        "siem",
        "ids",
        "ips",
    ],
    "ai_competition": [
        "ai",
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "neural",
        "model",
        "llm",
        "benchmark",
        "leaderboard",
        "arena",
        "competition",
        "race",
        "rival",
        "versus",
        "vs",
        "comparison",
        "outperform",
        "surpass",
        "beat",
        "match",
        "parameter",
        "transformer",
        "attention",
        "mixture of experts",
        "moe",
        "quantization",
        "fine-tuning",
        "pre-training",
        "inference",
        "latency",
        "throughput",
        "token",
        "context window",
        "multimodal",
        "agent",
        "agentic",
        "swarm",
        "orchestration",
    ],
    "developer_skills": [
        "tutorial",
        "skill",
        "dev",
        "developer",
        "programming",
        "coding",
        "best practice",
        "pattern",
        "architecture",
        "refactoring",
        "clean code",
        "solid",
        "dry",
        "kiss",
        "design pattern",
        "microservice",
        "monolith",
        "api",
        "rest",
        "graphql",
        "grpc",
        "database",
        "sql",
        "nosql",
        "cache",
        "queue",
        "event",
        "ci/cd",
        "devops",
        "sre",
        "observability",
        "monitoring",
        "logging",
        "tracing",
        "testing",
        "tdd",
        "unit test",
        "integration test",
        "e2e",
    ],
    "source_code": [
        "leak",
        "vazou",
        "source code",
        "repository",
        "github",
        "gitlab",
        "bitbucket",
        "npm",
        "package",
        "codebase",
        "open source",
        "opensource",
        "foss",
        "license",
        "apache",
        "mit",
        "gpl",
        "commit",
        "pull request",
        "merge",
        "branch",
        "diff",
        "patch",
        "reverse engineering",
        "decompilation",
        "binary",
        "firmware",
        "sdk",
    ],
    "social_engineering": [
        "social engineering",
        "spear phishing",
        "pretexting",
        "baiting",
        "quid pro quo",
        "tailgating",
        "impersonation",
        "identity theft",
        "fraud",
        "scam",
        "deepfake",
        "voice clone",
        "manipulation",
        "psychological",
        "trust",
        "authority",
        "urgency",
        "fear",
        "curiosity",
        "greed",
    ],
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
