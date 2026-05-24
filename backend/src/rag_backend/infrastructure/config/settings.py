"""Application settings using Pydantic Settings."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from rag_backend.domain.constants import ENCODING_UTF8


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

    langsmith_api_key: SecretStr | None = None
    langsmith_project: str = "rag-backend"
    langsmith_tracing: bool = False

    langfuse_secret_key: SecretStr | None = None
    langfuse_public_key: str = ""
    langfuse_host: str = "http://langfuse:3000"

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

    feature_flag_editorial_workflow: bool = True
    feature_flag_quality_checks: bool = True
    feature_flag_workflow_board: bool = True
    feature_flag_content_calendar: bool = True
    workflow_alerts_enabled: bool = True

    @property
    def feature_flags(self) -> dict[str, bool]:
        """Feature flag map for gradual rollout (DEPLOY-003)."""
        from rag_backend.domain.constants.feature_flags import (
            FLAG_CONTENT_CALENDAR,
            FLAG_EDITORIAL_WORKFLOW,
            FLAG_QUALITY_CHECKS,
            FLAG_WORKFLOW_BOARD,
        )

        return {
            FLAG_EDITORIAL_WORKFLOW: self.feature_flag_editorial_workflow,
            FLAG_QUALITY_CHECKS: self.feature_flag_quality_checks,
            FLAG_WORKFLOW_BOARD: self.feature_flag_workflow_board,
            FLAG_CONTENT_CALENDAR: self.feature_flag_content_calendar,
        }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
