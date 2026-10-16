"""Provider-agnostic chat-model factory (AE-0285).

The backend's chat LLM is selectable between Anthropic (Claude) and GLM (via the
OpenCode Go OpenAI-compatible endpoint) so carousel/chat generation can run on
GLM 5.2 to cut Anthropic spend, with Anthropic kept as a toggleable fallback.

Every consumer only depends on the LangChain ``BaseChatModel`` contract, so the
provider is swapped here with no downstream change.
"""

import uuid

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from rag_backend.application.services.carousel.editorial_workflow_types import (
    ChatModelRoles,
)
from rag_backend.infrastructure.config.llm_routing_constants import (
    LLM_ROLE_FAST,
    LLM_ROLE_REASONING,
    LLM_TIMEOUT_FAST_SECONDS,
    LLM_TIMEOUT_REASONING_SECONDS,
)
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.routed_chat_model import RoutedChatModel

LLM_PROVIDER_ANTHROPIC = "anthropic"
LLM_PROVIDER_GLM = "glm"

# Shared generation defaults (kept identical across providers so a swap does not
# silently change output length/behaviour). 32K tokens: bilingual PT+EN slide
# arrays plus two full blog posts overflow smaller caps mid-JSON.
_TEMPERATURE = 0.7
_MAX_TOKENS = 32000
_MAX_RETRIES = 3

# AE-0330: OpenCode Go rejects every request that carries no conversation header
# with ``400 MissingSessionID`` ("Request is missing x-opencode-session and
# cannot be routed efficiently"), which the workflow-start route then surfaced as
# a 503 ``provider_unavailable`` — observed live in prod 2026-09-14. Their docs
# also ask callers to identify with their own user agent instead of the generic
# ``OpenAI/Python`` the SDK sends by default. Both go on the client as default
# headers so every call made through it complies.
_OPENCODE_SESSION_HEADER = "x-opencode-session"
_USER_AGENT_HEADER = "User-Agent"
_OPENCODE_SESSION_PREFIX = "alter-ego-"
_USER_AGENT_PREFIX = "alter-ego/"

logger = structlog.get_logger(__name__)


def _opencode_headers(settings: Settings) -> dict[str, str]:
    """Default headers the OpenCode Go endpoint requires of API callers.

    The session id is minted once per client and therefore stays stable for the
    life of the process (the chat model is a DI singleton), which is what their
    routing and prompt-cache optimisation expects of a "conversation".
    """
    return {
        _OPENCODE_SESSION_HEADER: f"{_OPENCODE_SESSION_PREFIX}{uuid.uuid4()}",
        _USER_AGENT_HEADER: f"{_USER_AGENT_PREFIX}{settings.app_version}",
    }


def _build_glm_model(settings: Settings, model: str | None = None) -> ChatOpenAI:
    """A model (GLM by default) via the OpenCode Go OpenAI-compatible endpoint.

    AE-0391: the same endpoint/key/session header serves the DeepSeek models,
    so ``model`` selects any id the endpoint lists.
    """
    return ChatOpenAI(
        api_key=settings.glm_api_key,
        base_url=settings.glm_base_url,
        model=model or settings.glm_model,
        temperature=_TEMPERATURE,
        streaming=True,
        max_tokens=_MAX_TOKENS,
        max_retries=_MAX_RETRIES,
        default_headers=_opencode_headers(settings),
    )


def _build_anthropic_model(settings: Settings) -> ChatAnthropic:
    """Claude (Sonnet by default) via the Anthropic API."""
    return ChatAnthropic(
        api_key=settings.anthropic_api_key,
        model=settings.anthropic_model,
        temperature=_TEMPERATURE,
        streaming=True,
        max_tokens=_MAX_TOKENS,
        max_retries=_MAX_RETRIES,
    )


def _role_model_id(settings: Settings, role: str) -> str:
    return {
        LLM_ROLE_REASONING: settings.llm_model_reasoning,
        LLM_ROLE_FAST: settings.llm_model_fast,
    }.get(role, settings.glm_model)


def _role_fallback_id(settings: Settings, role: str) -> str:
    """AE-0395: each role falls back to its own fast model (no longer GLM)."""
    return {
        LLM_ROLE_REASONING: settings.llm_model_fallback_reasoning,
    }.get(role, settings.llm_model_fallback)


def _build_routed_model(settings: Settings, role: str) -> RoutedChatModel:
    """AE-0391: the role's model with a per-call timeout and its fallback."""
    return RoutedChatModel(
        primary=_build_glm_model(settings, _role_model_id(settings, role)),
        fallback=_build_glm_model(settings, _role_fallback_id(settings, role)),
        role=role,
        timeout_seconds=_ROLE_TIMEOUTS.get(role, LLM_TIMEOUT_REASONING_SECONDS),
    )


_ROLE_TIMEOUTS: dict[str, float] = {
    LLM_ROLE_REASONING: LLM_TIMEOUT_REASONING_SECONDS,
    LLM_ROLE_FAST: LLM_TIMEOUT_FAST_SECONDS,
}


def build_chat_model(settings: Settings, role: str | None = None) -> BaseChatModel:
    """Return the configured chat model.

    ``llm_provider="glm"`` selects GLM **only when a GLM key is present**; with an
    empty key (CI, or a prod not yet given the secret) it falls back to Anthropic
    and warns, so a missing key degrades gracefully instead of breaking generation.

    AE-0391: a ``role`` (reasoning / fast) routes the call to that role's model
    on the OpenCode Go endpoint, wrapped with the GLM fallback. Without a role
    (chat / RAG agents) the single ``glm_model`` is built as before.
    """
    if settings.llm_provider != LLM_PROVIDER_GLM:
        return _build_anthropic_model(settings)
    if not settings.glm_api_key.get_secret_value():
        logger.warning(
            "llm_provider_glm_without_key_falling_back_to_anthropic",
            glm_base_url=settings.glm_base_url,
        )
        return _build_anthropic_model(settings)
    if role is None:
        return _build_glm_model(settings)
    return _build_routed_model(settings, role)


def build_role_models(settings: Settings) -> ChatModelRoles:
    """AE-0391: the carousel pipeline's reasoning and fast chat models."""
    return ChatModelRoles(
        reasoning=build_chat_model(settings, LLM_ROLE_REASONING),
        fast=build_chat_model(settings, LLM_ROLE_FAST),
        draft_concurrency=settings.content_draft_concurrency,
    )
