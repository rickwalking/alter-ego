"""Application settings using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import SettingsConfigDict

from rag_backend.domain.constants import ENCODING_UTF8
from rag_backend.domain.constants.blog_generation import (
    DEFAULT_BLOG_GENERATION_STALE_SECONDS,
    DEFAULT_BLOG_GENERATION_TIMEOUT_SECONDS,
    DEFAULT_BLOG_IMAGE_CONCURRENCY,
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
    # GLM 5.3 is a reasoning model (emits chain-of-thought before the answer), so
    # the 32K max_tokens in the factory matters — a small budget is consumed by
    # reasoning before any content is produced. Model id uses a dot (verified
    # live against the endpoint): "glm-5.3", not "glm-5-3".
    #
    # AE-0330: moved up from 5.2 after 5.2 spent 31999 of its 32000 tokens
    # reasoning on an outline prompt and returned empty content, failing the
    # phase live on 2026-09-14. Sampled against the same prompt shape, 5.3 held
    # a tight 1605-1808 reasoning tokens where 5.2 ranged 49-31999. That is
    # suggestive, NOT proof it cannot spiral — a tail event will not show in a
    # handful of samples, which is exactly how 5.2 looked healthy right before
    # it failed. The llm_json_retry re-roll is what actually makes a bad sample
    # survivable; this swap is a narrower distribution on top of it, not a
    # replacement for it. Watch the persona voice-match (>= 70) on PT copy.
    glm_model: str = "glm-5.3"
    # AE-0391: per-task carousel models on the same OpenCode Go endpoint/key.
    # Reasoning: research synthesis, outline, quality/rubric judgement. Fast:
    # slide drafting, translation, distribution copy, refinement, persona
    # scoring. Fallback: used when the primary call fails (error, timeout,
    # empty content, bad JSON after the retry). Ignored unless the GLM provider
    # is active with a key (Anthropic semantics are unchanged).
    llm_model_reasoning: str = DEFAULT_LLM_MODEL_REASONING
    llm_model_fast: str = DEFAULT_LLM_MODEL_FAST
    llm_model_fallback: str = DEFAULT_LLM_MODEL_FALLBACK
    llm_model_fallback_reasoning: str = DEFAULT_LLM_MODEL_FALLBACK_REASONING
    # AE-0399: per-role model queues ("<transport>:<model>" entries, in order;
    # empty keeps the AE-0391 primary + fallback routing), the circuit breaker
    # and the OpenCode sidecar (``opencode serve``) that hosts the free model.
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
    # AE-0399: send-only Telegram bot for model failures and breaker changes.
    telegram_alerts_bot_token: SecretStr = SecretStr("")
    telegram_alerts_chat_id: str = ""
    # AE-0391: slides drafted concurrently in the content phase (>= 1).
    content_draft_concurrency: int = Field(
        default=DEFAULT_CONTENT_DRAFT_CONCURRENCY, ge=1
    )

    # AE-0317 kill switch: when false, workflow-start web research (URL scraping
    # + DuckDuckGo topic search) is skipped and sources pass through unchanged.
    research_enrichment_enabled: bool = True

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
    # Instagram Login tokens (IGAA…) only work against graph.instagram.com.
    # Page tokens set this to https://graph.facebook.com/v23.0.
    meta_ig_graph_base: str = GRAPH_HOST_INSTAGRAM
    # AE-0358: Fernet key for integration_credentials. Empty disables
    # autopilot Instagram publishing and logs a startup warning.
    credentials_encryption_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices(
            "CREDENTIALS_ENCRYPTION_KEY",
            "credentials_encryption_key",
        ),
    )

    # AE-0351: sha256 hex digest of the scout API key. Empty disables
    # /api/autopilot/* (HTTP 503). The plaintext key is never stored.
    grokbot_api_key_sha256: SecretStr = SecretStr("")

    # AE-0352: X post enrichment. "none" (the default) never requests x.com
    # or a mirror. "mirror" rewrites a status URL to
    # https://{autopilot_x_mirror_host}/{handle}/status/{id}. The host is a
    # hostname, not a URL. Leave the resolver at none while mirrors return 451.
    autopilot_x_resolver: Literal["none", "mirror"] = "none"
    autopilot_x_mirror_host: str = ""
    # Optional GitHub Search token. Empty uses the unauthenticated API.
    github_token: SecretStr = SecretStr("")
    # AE-0353: queued autopilot runs allowed per America/Sao_Paulo day.
    # Keep the default aligned with autopilot.constants.DEFAULT_DAILY_CAP.
    autopilot_daily_cap: int = Field(
        default=1,
        ge=0,
        validation_alias=AliasChoices("AUTOPILOT_DAILY_CAP", "autopilot_daily_cap"),
    )
    # AE-0355: empty token or chat id makes the notifier a no-op logger.
    # The runner then escalates final review with notifier_unconfigured.
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_owner_chat_id: str = ""
    # AE-0356: empty rejects POST /api/telegram/webhook with HTTP 401.
    telegram_webhook_secret: SecretStr = SecretStr("")

    # AE-0354: the worker calls the in-process runner only when this is true.
    autopilot_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("AUTOPILOT_ENABLED", "autopilot_enabled"),
    )
    # Existing user id the created carousels are owned by. reviewer_id stays unset.
    autopilot_owner_user_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "AUTOPILOT_OWNER_USER_ID",
            "autopilot_owner_user_id",
        ),
    )

    # AE-0370: what Approve does on Telegram. "now" offers publish-now or a
    # schedule; "next_slot" schedules the next good slot directly.
    autopilot_default_publish: Literal["now", "next_slot"] = Field(
        default="now",
        validation_alias=AliasChoices(
            "AUTOPILOT_DEFAULT_PUBLISH",
            "autopilot_default_publish",
        ),
    )

    # AE-0371 (PR #106 review): the persona that voices autopilot carousels.
    # Empty: the persona named "Pedro" is used; none: POV runs escalate unscored.
    autopilot_persona_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "AUTOPILOT_PERSONA_ID",
            "autopilot_persona_id",
        ),
    )

    carousel_public_base_url: str = ""

    # AE-0393 (ADR-0022): carousel images through the Grok Bot webhook, with
    # OpenAI as the fallback. Off here (dev/tests make no webhook calls); prod
    # deploy.yml turns it on. Enabled without the webhook URL or the public base
    # URL, startup logs image_bridge_misconfigured and keeps plain OpenAI.
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

    # AE-0424 (ADR-0025): the single-author deployment may review its own blog
    # posts. Bypasses only the submit-time ERR_SELF_REVIEW guard and stores the
    # author as reviewer_id; off by default (a distinct reviewer is required).
    blog_allow_self_review: bool = False
    # AE-0424: images generated per post (cover + sections, regenerations
    # included) before generation is refused; the spend ceiling of ADR-0025.
    blog_image_cost_cap: int = Field(default=30, ge=1)

    otel_enabled: bool = False
    otel_exporter_endpoint: str = ""
    otel_service_name: str = "rag-backend"

    redis_url: str = ""
    # AE-0302: managed Redis credential; required (fail-closed) whenever the
    # environment is production-like — see redis_clients.factory.
    redis_password: SecretStr = SecretStr("")
    workflow_worker_interval_seconds: int = 60
    # AE-0210: auto-reject workflows stuck past this threshold (never-stuck rule).
    workflow_auto_reject_enabled: bool = True
    workflow_stuck_timeout_hours: int = 72
    # AE-0315: run-progress heartbeat + stale-run reaper. The background resume
    # task heartbeats every `heartbeat_seconds`; a heartbeat older than
    # `heartbeat_stale_seconds` counts as one stale observation; the reaper
    # flips a run only after `reap_observations` CONSECUTIVE stale ticks
    # (never on NULL heartbeats — those alert only). Wall-clock age past
    # `overdue_minutes` only ever alerts, never reaps.
    workflow_run_heartbeat_seconds: int = 60
    workflow_run_heartbeat_stale_seconds: int = 180
    workflow_run_reap_observations: int = 3
    workflow_run_overdue_minutes: int = 60
    # AE-0425 (ADR-0025): blog writer + GPT images. Concurrency of the image
    # step (the per-post cap is AE-0424's blog_image_cost_cap), the run bound
    # and the heartbeat age after which the worker-tick reaper fails a run.
    blog_image_concurrency: int = Field(default=DEFAULT_BLOG_IMAGE_CONCURRENCY, ge=1)
    blog_generation_timeout_seconds: int = Field(
        default=DEFAULT_BLOG_GENERATION_TIMEOUT_SECONDS, ge=1
    )
    blog_generation_stale_seconds: int = Field(
        default=DEFAULT_BLOG_GENERATION_STALE_SECONDS, ge=1
    )

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

    def image_provider_api_key(self, provider: str) -> SecretStr | None:
        """API-key secret for a carousel image provider; ``None`` if unknown.

        Single source of truth for the provider→key wiring (AE-0308): the
        AE-0215 startup guard and the request-time creation guard both consult
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
