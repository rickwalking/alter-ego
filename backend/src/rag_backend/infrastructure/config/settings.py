"""Application settings using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import SettingsConfigDict

from rag_backend.domain.constants import ENCODING_UTF8
from rag_backend.domain.constants.autopilot_start import (
    DEFAULT_START_SPACING_MINUTES,
)
from rag_backend.domain.constants.blog_generation import (
    DEFAULT_BLOG_GENERATION_STALE_SECONDS,
    DEFAULT_BLOG_GENERATION_TEXT_TIMEOUT_SECONDS,
    DEFAULT_BLOG_IMAGE_CONCURRENCY,
    DEFAULT_BLOG_IMAGE_WAVE_TIMEOUT_SECONDS,
)
from rag_backend.domain.constants.carousel_archive import (
    CAROUSEL_AUTO_ARCHIVE_DEFAULT_DAYS,
)
from rag_backend.domain.constants.instagram_publish import GRAPH_HOST_INSTAGRAM
from rag_backend.infrastructure.config.autopilot_autofix_settings import (
    AutopilotAutofixSettings,
)
from rag_backend.infrastructure.config.constants import (
    ENVIRONMENT_DEVELOPMENT,
    NON_PRODUCTION_ENVIRONMENTS,
)
from rag_backend.infrastructure.config.llm_queue_constants import (
    DEFAULT_BREAKER_COOLDOWN_SECONDS,
    DEFAULT_BREAKER_FAILURES,
    DEFAULT_BREAKER_FATAL_COOLDOWN_SECONDS,
    DEFAULT_BREAKER_QUOTA_COOLDOWN_SECONDS,
    DEFAULT_SIDECAR_CONCURRENCY,
    DEFAULT_SIDECAR_TIMEOUT_SECONDS,
)
from rag_backend.infrastructure.config.llm_routing_constants import (
    DEFAULT_CONTENT_DRAFT_CONCURRENCY,
    DEFAULT_LLM_MODEL_FALLBACK,
    DEFAULT_LLM_MODEL_FALLBACK_REASONING,
    DEFAULT_LLM_MODEL_FAST,
    DEFAULT_LLM_MODEL_REASONING,
)


class Settings(AutopilotAutofixSettings):
    """Application settings loaded from environment variables.

    Field notes:

    - ``environment`` drives the startup hardening checks (durable checkpointer,
      image-provider keys); prod/staging deploys must set
      ``ENVIRONMENT=production``.
    - ``llm_provider``: ``glm`` routes carousel/chat/RAG agents to GLM via the
      OpenCode Go OpenAI-compatible endpoint; ``anthropic`` keeps Claude. With
      ``glm`` but an empty ``glm_api_key`` the factory falls back to Anthropic
      (safe for CI / unconfigured prod).
    - ``glm_model``: GLM 5.3 is a reasoning model, so the factory's 32K max_tokens
      matters (a small budget is spent on reasoning before any content). The id
      uses a dot (verified live): ``glm-5.3``. 5.2 once spent 31999 of 32000
      tokens reasoning and returned empty content; 5.3 sampled tighter, which is
      suggestive, not proof. The ``llm_json_retry`` re-roll is what makes a bad
      sample survivable. Watch the persona voice-match (>= 70) on PT copy.
    - ``llm_model_*`` are per-task carousel models on the same endpoint/key:
      reasoning (research synthesis, outline, rubric judgement), fast (drafting,
      translation, distribution copy, refinement, persona scoring) and fallback
      (when the primary fails: error, timeout, empty, bad JSON after the retry).
      Ignored unless the GLM provider is active with a key.
    - ``llm_model_queue_*`` are per-role queues (``<transport>:<model>`` entries in
      order; empty keeps primary + fallback routing), next to the circuit breaker
      and the OpenCode sidecar (``opencode serve``) hosting the free model.
      ``telegram_alerts_*`` is the send-only bot for model failures and breaker
      changes.
    - ``research_enrichment_enabled`` is a kill switch: when false, workflow-start
      URL scraping + DuckDuckGo search is skipped and sources pass through.
    - ``carousel_image_concurrency`` stays at/below the image provider's per-minute
      org cap (gpt-image: 5/min) so a multi-slide carousel does not 429; retries
      honour the provider's ``retry-after``.
    - ``meta_ig_graph_base``: Instagram Login tokens (IGAA...) only work against
      graph.instagram.com; page tokens set https://graph.facebook.com/v23.0.
    - ``credentials_encryption_key`` is the Fernet key for
      ``integration_credentials``; empty disables autopilot Instagram publishing and
      logs a startup warning.
    - ``grokbot_api_key_sha256`` is the scout key's sha256 hex digest (the
      plaintext is never stored); empty disables ``/api/autopilot/*`` (HTTP 503).
    - ``autopilot_x_resolver``: ``none`` never requests x.com or a mirror;
      ``mirror`` rewrites a status URL to
      ``https://{autopilot_x_mirror_host}/{handle}/status/{id}`` (a hostname, not a
      URL). Keep ``none`` while mirrors return 451. An empty ``github_token`` uses
      the unauthenticated Search API.
    - ``autopilot_daily_cap`` counts queued runs per America/Sao_Paulo day; keep it
      aligned with ``autopilot.constants.DEFAULT_DAILY_CAP``.
    - An empty ``telegram_bot_token`` or chat id makes the notifier a no-op logger
      and the runner escalates final review with ``notifier_unconfigured``. An empty
      ``telegram_webhook_secret`` rejects the webhook with HTTP 401.
    - The worker calls the in-process runner only when ``autopilot_enabled``.
      ``autopilot_owner_user_id`` is an existing user owning the created carousels
      (reviewer_id stays unset). It is the site owner: only conversations and
      knowledge searches of this user read personal knowledge; unset, every chat
      and search reads public knowledge only.
    - ``autopilot_default_publish``: ``now`` offers publish-now or a schedule on
      Approve; ``next_slot`` schedules the next good slot directly.
    - ``autopilot_start_spacing_minutes``: minimum minutes between two autopilot
      generation starts (default 20, 0 is off).
    - ``autopilot_persona_id`` voices autopilot carousels: empty uses the persona
      named "Pedro"; with none, POV runs escalate unscored.
    - ``image_bridge_enabled`` sends carousel images through the Grok Bot webhook
      with OpenAI as fallback (ADR-0022). Off by default (dev/tests make no webhook
      calls); prod deploy turns it on. Enabled without the webhook or public base
      URL, startup logs ``image_bridge_misconfigured`` and keeps plain OpenAI.
    - ``blog_image_cost_cap`` is the per-post image spend ceiling (cover + sections,
      regenerations included) of ADR-0025. ``blog_image_concurrency`` bounds the
      image step; the image stage budget is the per-wave budget x
      ceil(slots / concurrency).
    - ``redis_password`` is required (fail-closed) in production-like environments;
      see ``redis_clients.factory``.
    - ``workflow_stuck_timeout_hours`` drives the auto-reject of stuck workflows.
    - ``carousel_auto_archive_days``: a carousel idle for more than this many days
      is archived by the workflow worker (``0`` turns auto-archive off).
    - Run heartbeat + stale-run reaper: the resume task heartbeats every
      ``heartbeat_seconds``; a heartbeat older than ``heartbeat_stale_seconds`` is
      one stale observation; the reaper flips a run only after
      ``reap_observations`` CONSECUTIVE stale ticks (NULL heartbeats only alert).
      Wall-clock age past ``overdue_minutes`` only alerts, never reaps.
    - ``feature_flag_palette_catalog`` defaults on in every environment, production
      included (the frontend consumes the catalog; co-deploy with it).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding=ENCODING_UTF8,
        case_sensitive=False,
    )

    app_name: str = "RAG Backend"
    app_version: str = "0.1.0"
    debug: bool = False
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

    llm_provider: str = "glm"
    glm_api_key: SecretStr = SecretStr("")
    glm_base_url: str = "https://opencode.ai/zen/go/v1"
    glm_model: str = "glm-5.3"
    llm_model_reasoning: str = DEFAULT_LLM_MODEL_REASONING
    llm_model_fast: str = DEFAULT_LLM_MODEL_FAST
    llm_model_fallback: str = DEFAULT_LLM_MODEL_FALLBACK
    llm_model_fallback_reasoning: str = DEFAULT_LLM_MODEL_FALLBACK_REASONING
    llm_model_queue_fast: str = ""
    llm_model_queue_reasoning: str = ""
    llm_breaker_failures: int = Field(default=DEFAULT_BREAKER_FAILURES, ge=1)
    llm_breaker_cooldown_seconds: float = DEFAULT_BREAKER_COOLDOWN_SECONDS
    llm_breaker_quota_cooldown_seconds: float = DEFAULT_BREAKER_QUOTA_COOLDOWN_SECONDS
    llm_breaker_fatal_cooldown_seconds: float = DEFAULT_BREAKER_FATAL_COOLDOWN_SECONDS
    opencode_sidecar_url: str = ""
    opencode_server_password: SecretStr = SecretStr("")
    opencode_sidecar_timeout_seconds: float = DEFAULT_SIDECAR_TIMEOUT_SECONDS
    opencode_sidecar_concurrency: int = Field(default=DEFAULT_SIDECAR_CONCURRENCY, ge=1)
    telegram_alerts_bot_token: SecretStr = SecretStr("")
    telegram_alerts_chat_id: str = ""
    content_draft_concurrency: int = Field(
        default=DEFAULT_CONTENT_DRAFT_CONCURRENCY, ge=1
    )

    research_enrichment_enabled: bool = True

    langsmith_api_key: SecretStr | None = None
    langsmith_project: str = "rag-backend"
    langsmith_tracing: bool = False

    langfuse_secret_key: SecretStr | None = None
    langfuse_public_key: str = ""
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
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
    meta_ig_graph_base: str = GRAPH_HOST_INSTAGRAM
    credentials_encryption_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices(
            "CREDENTIALS_ENCRYPTION_KEY",
            "credentials_encryption_key",
        ),
    )

    grokbot_api_key_sha256: SecretStr = SecretStr("")

    autopilot_x_resolver: Literal["none", "mirror"] = "none"
    autopilot_x_mirror_host: str = ""
    github_token: SecretStr = SecretStr("")
    autopilot_daily_cap: int = Field(
        default=1,
        ge=0,
        validation_alias=AliasChoices("AUTOPILOT_DAILY_CAP", "autopilot_daily_cap"),
    )
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_owner_chat_id: str = ""
    telegram_webhook_secret: SecretStr = SecretStr("")

    autopilot_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("AUTOPILOT_ENABLED", "autopilot_enabled"),
    )
    autopilot_owner_user_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "AUTOPILOT_OWNER_USER_ID",
            "autopilot_owner_user_id",
        ),
    )

    autopilot_default_publish: Literal["now", "next_slot"] = Field(
        default="now",
        validation_alias=AliasChoices(
            "AUTOPILOT_DEFAULT_PUBLISH",
            "autopilot_default_publish",
        ),
    )

    autopilot_start_spacing_minutes: int = Field(
        default=DEFAULT_START_SPACING_MINUTES,
        ge=0,
        validation_alias=AliasChoices(
            "AUTOPILOT_START_SPACING_MINUTES",
            "autopilot_start_spacing_minutes",
        ),
    )

    autopilot_persona_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "AUTOPILOT_PERSONA_ID",
            "autopilot_persona_id",
        ),
    )

    carousel_public_base_url: str = ""

    image_bridge_enabled: bool = False
    image_bridge_fallback_enabled: bool = True
    image_bridge_timeout_seconds: int = Field(default=600, ge=1)
    image_bridge_max_concurrency: int = Field(default=2, ge=1)
    image_bridge_public_base_url: str = ""
    grokbot_image_webhook_url: SecretStr = SecretStr("")
    grokbot_image_webhook_auth_header: str = "Authorization"
    grokbot_image_webhook_auth_value: SecretStr = SecretStr("")

    cdn_base_url: str = ""
    cdn_enabled: bool = False

    blog_image_cost_cap: int = Field(default=30, ge=1)

    otel_enabled: bool = False
    otel_exporter_endpoint: str = ""
    otel_service_name: str = "rag-backend"

    redis_url: str = ""
    redis_password: SecretStr = SecretStr("")
    workflow_worker_interval_seconds: int = 60
    workflow_auto_reject_enabled: bool = True
    workflow_stuck_timeout_hours: int = 72
    carousel_auto_archive_days: int = Field(
        default=CAROUSEL_AUTO_ARCHIVE_DEFAULT_DAYS, ge=0
    )
    workflow_run_heartbeat_seconds: int = 60
    workflow_run_heartbeat_stale_seconds: int = 180
    workflow_run_reap_observations: int = 3
    workflow_run_overdue_minutes: int = 60
    blog_image_concurrency: int = Field(default=DEFAULT_BLOG_IMAGE_CONCURRENCY, ge=1)
    blog_generation_text_timeout_seconds: int = Field(
        default=DEFAULT_BLOG_GENERATION_TEXT_TIMEOUT_SECONDS, ge=1
    )
    blog_image_wave_timeout_seconds: int = Field(
        default=DEFAULT_BLOG_IMAGE_WAVE_TIMEOUT_SECONDS, ge=1
    )
    blog_generation_stale_seconds: int = Field(
        default=DEFAULT_BLOG_GENERATION_STALE_SECONDS, ge=1
    )

    feature_flag_editorial_workflow: bool = True
    feature_flag_quality_checks: bool = True
    feature_flag_workflow_board: bool = True
    feature_flag_content_calendar: bool = True
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

    def image_provider_api_key(self, provider: str) -> SecretStr | None:
        """API-key secret for a carousel image provider; ``None`` if unknown.

        Single source of truth for the provider→key wiring: the
        startup guard and the request-time creation guard both consult
        this mapping, so they can never disagree about which providers are
        usable on this deployment.
        """
        from rag_backend.domain.constants import (
            IMAGE_MODEL_GEMINI,
            IMAGE_MODEL_OPENAI,
        )

        keys: dict[str, SecretStr] = {
            IMAGE_MODEL_GEMINI: self.gemini_api_key,
            IMAGE_MODEL_OPENAI: self.openai_api_key,
        }
        return keys.get(provider)

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
