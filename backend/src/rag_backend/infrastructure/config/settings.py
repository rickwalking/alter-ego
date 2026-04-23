"""Application settings using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "RAG Backend"
    app_version: str = "0.1.0"
    debug: bool = False
    allowed_origins: str = "*"

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost/rag_db"
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # Vector Store (Pinecone)
    pinecone_api_key: str = ""
    pinecone_index_name: str = "rag-index"
    pinecone_environment: str = "us-east-1"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-large"

    # Anthropic — pydantic-settings reads ANTHROPIC_API_KEY from .env/env
    # automatically via the case-insensitive field match. No manual
    # os.getenv call needed.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # LangSmith (optional, for monitoring)
    langsmith_api_key: str | None = None
    langsmith_project: str = "rag-backend"
    langsmith_tracing: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Search
    default_search_alpha: float = 0.5
    default_top_k: int = 5
    max_chunks_per_document: int = 1000

    # Upload
    max_upload_size_mb: int = 50

    # Security
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60

    # Gemini (for carousel image generation)
    gemini_api_key: str = ""

    # Carousel
    carousel_output_dir: str = "./output/carousels"
    # Which checkpointer backend the carousel LangGraph pipeline uses:
    #   - "sqlite"   → AsyncSqliteSaver on `carousel_checkpoint_sqlite_path` (dev)
    #   - "postgres" → AsyncPostgresSaver on `carousel_checkpoint_postgres_url` (prod)
    #   - "memory"   → InMemorySaver (ephemeral — loses state on restart)
    #   - "disabled" → no checkpointer (no /resume, no mid-pipeline recovery)
    carousel_checkpoint_backend: str = "sqlite"
    carousel_checkpoint_sqlite_path: str = "./output/carousel_checkpoints.sqlite"
    # Postgres connection string in psycopg form (`postgresql://user:pw@host/db`) —
    # distinct from `database_url` which uses the SQLAlchemy-asyncpg dialect.
    # Empty in dev; set in prod.
    carousel_checkpoint_postgres_url: str = ""
    # Cron-job TTL: projects in COMPLETED or FAILED status older than this
    # get their checkpoint threads reaped by `scripts/cleanup_carousel_checkpoints.py`.
    carousel_checkpoint_ttl_days: int = 30

    # LinkedIn voice cloning: comma-separated URLs of the user's own posts
    # (public share URLs). The LinkedIn post generator scrapes previews from
    # these and feeds them as few-shot examples. Empty → default neutral voice.
    writing_style_urls: str = ""
    writing_style_cache_dir: str = "./output/writing_style_cache"

    # Instagram publishing via Meta Graph API. Both must be set for the
    # /api/carousels/{id}/publish/instagram route to succeed; otherwise
    # the route returns 503 with an actionable hint.
    meta_ig_access_token: str = ""
    meta_ig_user_id: str = ""

    # Public HTTPS base URL for serving /api/carousels/{id}/images/*.
    # Meta's fetchers need a reachable URL; localhost won't work for
    # publishing. Empty → publisher refuses with an explanatory error.
    carousel_public_base_url: str = ""


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
