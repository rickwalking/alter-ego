"""Provider-agnostic chat-model factory (AE-0285).

The backend's chat LLM is selectable between Anthropic (Claude) and GLM (via the
OpenCode Go OpenAI-compatible endpoint) so carousel/chat generation can run on
GLM 5.2 to cut Anthropic spend, with Anthropic kept as a toggleable fallback.

Every consumer only depends on the LangChain ``BaseChatModel`` contract, so the
provider is swapped here with no downstream change.
"""

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from rag_backend.infrastructure.config.settings import Settings

LLM_PROVIDER_ANTHROPIC = "anthropic"
LLM_PROVIDER_GLM = "glm"

# Shared generation defaults (kept identical across providers so a swap does not
# silently change output length/behaviour). 32K tokens: bilingual PT+EN slide
# arrays plus two full blog posts overflow smaller caps mid-JSON.
_TEMPERATURE = 0.7
_MAX_TOKENS = 32000
_MAX_RETRIES = 3

logger = structlog.get_logger(__name__)


def _build_glm_model(settings: Settings) -> ChatOpenAI:
    """GLM 5.2 via the OpenCode Go OpenAI-compatible endpoint."""
    return ChatOpenAI(
        api_key=settings.glm_api_key,
        base_url=settings.glm_base_url,
        model=settings.glm_model,
        temperature=_TEMPERATURE,
        streaming=True,
        max_tokens=_MAX_TOKENS,
        max_retries=_MAX_RETRIES,
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


def build_chat_model(settings: Settings) -> BaseChatModel:
    """Return the configured chat model.

    ``llm_provider="glm"`` selects GLM **only when a GLM key is present**; with an
    empty key (CI, or a prod not yet given the secret) it falls back to Anthropic
    and warns, so a missing key degrades gracefully instead of breaking generation.
    """
    if settings.llm_provider == LLM_PROVIDER_GLM:
        if settings.glm_api_key.get_secret_value():
            return _build_glm_model(settings)
        logger.warning(
            "llm_provider_glm_without_key_falling_back_to_anthropic",
            glm_base_url=settings.glm_base_url,
        )
    return _build_anthropic_model(settings)
