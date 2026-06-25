"""Application settings using Pydantic Settings."""

from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from rag_backend.domain.constants import ENCODING_UTF8
from rag_backend.infrastructure.config.constants import (
    ENVIRONMENT_DEVELOPMENT,
    NON_PRODUCTION_ENVIRONMENTS,
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding=ENCODING_UTF8,
        case_sensitive=False,
    )

    app_name: str = "RAG Backend"
    app_version: str = "0.1.0"
    debug: bool = False
    # Deployment environment. Drives startup hardening checks (durable
    # checkpointer, image-provider keys). Local/test default keeps dev ergonomic;
    # prod/staging deploys must set ENVIRONMENT=production.
    environment: str = ENVIRONMENT_DEVELOPMENT
    allowed_origins: str = "*"

    database_url: str = "postgresql+asyncpg://user:password@localhost/rag_db"
    db_pool_size: int = 5
    db_max_overflow: int = 10

    pinecone_api_key: SecretStr = SecretStr("")
    pinecone_index_name: str = "rag-index"
    pinecone_environment: str = "us-east-1"

    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-large"

    anthropic_api_key: SecretStr = SecretStr("")
    anthropic_model: str = "claude-sonnet-4-6"

    # Chat-LLM provider toggle (AE-0285). "glm" routes carousel/chat/RAG agents
    # to GLM 5.2 via the OpenCode Go OpenAI-compatible endpoint to cut Anthropic
    # spend; "anthropic" keeps Claude. With provider="glm" but an empty
    # glm_api_key, the factory falls back to Anthropic (safe for CI / unconfigured
    # prod). Prod must set GLM_API_KEY as a secret to actually use GLM.
    llm_provider: str = "glm"
    glm_api_key: SecretStr = SecretStr("")
    glm_base_url: str = "https://opencode.ai/zen/go/v1"
    glm_model: str = "glm-5-2"

    langsmith_api_key: SecretStr | None = None
    langsmith_project: str = "rag-backend"
    langsmith_tracing: bool = False

    langfuse_secret_key: SecretStr | None = None
    langfuse_public_key: str = ""
    langfuse_host: str = Field(
        default="http://langfuse:3000",
        validation_alias=AliasChoices("langfuse_host", "langfuse_base_url"),
    )

    @field_validator("langfuse_host")
    @classmethod
    def _strip_langfuse_host_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    host: str = "0.0.0.0"
    port: int = 8000

    default_search_alpha: float = 0.5
    default_top_k: int = 5
    max_chunks_per_document: int = 1000

    max_upload_size_mb: int = 50

    secret_key: SecretStr
    anon_secret_key: SecretStr
    access_token_expire_minutes: int = 60
    anon_token_expire_minutes: int = 60

    gemini_api_key: SecretStr = SecretStr("")

    carousel_output_dir: str = "./output/carousels"
    carousel_creator_assets_dir: str = "./output/creator_assets"
    # AE-0208: cap concurrent image-provider calls at/below the documented
    # per-minute org cap (OpenAI gpt-image org limit is 5/min) so a multi-slide
    # carousel does not blow past it and 429. App-level retry attempts honor the
    # provider's ``retry-after`` so a transient 429 is survived, not fatal.
    carousel_image_concurrency: int = 5
    carousel_image_max_attempts: int = 5
    carousel_checkpoint_backend: str = "sqlite"
    carousel_checkpoint_sqlite_path: str = "./output/carousel_checkpoints.sqlite"
    carousel_checkpoint_postgres_url: str = ""
    carousel_checkpoint_ttl_days: int = 30

    writing_style_urls: str = ""
    writing_style_cache_dir: str = "./output/writing_style_cache"

    meta_ig_access_token: SecretStr = SecretStr("")
    meta_ig_user_id: str = ""

    carousel_public_base_url: str = ""

    cdn_base_url: str = ""
    cdn_enabled: bool = False

    otel_enabled: bool = False
    otel_exporter_endpoint: str = ""
    otel_service_name: str = "rag-backend"

    redis_url: str = ""
    workflow_worker_interval_seconds: int = 60
    # AE-0210: auto-reject workflows stuck past this threshold (never-stuck rule).
    workflow_auto_reject_enabled: bool = True
    workflow_stuck_timeout_hours: int = 72

    feature_flag_editorial_workflow: bool = True
    feature_flag_quality_checks: bool = True
    feature_flag_workflow_board: bool = True
    feature_flag_content_calendar: bool = True
    # AE-0271: the palette catalog goes live now that the frontend consumes it
    # (co-deploy with the FE — skeptical G6). Default True so this release flips the
    # AE-0270 CRUD endpoints on in every environment, including production.
    feature_flag_palette_catalog: bool = True
    workflow_alerts_enabled: bool = True

    @property
    def is_production_like(self) -> bool:
        """True when running outside the dev/test environments.

        Startup hardening guards (durable checkpointer, image-provider keys)
        treat staging and production as production-like and tolerate ephemeral
        configuration only in development/test.
        """
        return self.environment.strip().lower() not in NON_PRODUCTION_ENVIRONMENTS

    @property
    def feature_flags(self) -> dict[str, bool]:
        """Feature flag map for gradual rollout (DEPLOY-003)."""
        from rag_backend.domain.constants.feature_flags import (
            FLAG_CONTENT_CALENDAR,
            FLAG_EDITORIAL_WORKFLOW,
            FLAG_PALETTE_CATALOG,
            FLAG_QUALITY_CHECKS,
            FLAG_WORKFLOW_BOARD,
        )

        return {
            FLAG_EDITORIAL_WORKFLOW: self.feature_flag_editorial_workflow,
            FLAG_QUALITY_CHECKS: self.feature_flag_quality_checks,
            FLAG_WORKFLOW_BOARD: self.feature_flag_workflow_board,
            FLAG_CONTENT_CALENDAR: self.feature_flag_content_calendar,
            FLAG_PALETTE_CATALOG: self.feature_flag_palette_catalog,
        }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
