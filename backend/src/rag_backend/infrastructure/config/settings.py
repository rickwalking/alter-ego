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


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
