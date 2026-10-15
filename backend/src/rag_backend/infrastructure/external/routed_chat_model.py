"""Role-routed chat model with an automatic fallback model (AE-0391).

``RoutedChatModel`` is a ``BaseChatModel`` so every carousel consumer keeps its
contract (``ainvoke`` / ``bind`` / ``with_config``). It delegates each call to
the primary model of its role under a per-call timeout and, when that call
fails (any error except auth, a timeout, or empty content), re-issues the same
call on the fallback model, logging ``llm_fallback_used``.

``ainvoke`` is overridden so the wrapper adds no generation of its own to
Langfuse: the inner model's run is the generation, carrying the actual model
name plus ``role:<role>`` / ``model:<id>`` tags (and ``fallback:true`` on the
fallback). Token usage is therefore counted once.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import structlog
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult
from langchain_core.runnables import Runnable, RunnableBinding, RunnableConfig
from langchain_core.runnables.config import merge_configs

from rag_backend.infrastructure.config.llm_routing_constants import (
    AUTH_STATUS_CODES,
    FALLBACK_REASON_EMPTY,
    FALLBACK_REASON_ERROR,
    FALLBACK_REASON_TIMEOUT,
    LLM_METADATA_FALLBACK,
    LLM_METADATA_MODEL,
    LLM_METADATA_ROLE,
    LLM_TAG_FALLBACK,
    LLM_TAG_MODEL_PREFIX,
    LLM_TAG_ROLE_PREFIX,
    LLM_TIMEOUT_FALLBACK_SECONDS,
    LOG_LLM_FALLBACK_USED,
)

logger = structlog.get_logger(__name__)

_LLM_TYPE = "routed-chat-model"
_STATUS_CODE_ATTR = "status_code"
_MODEL_NAME_ATTRS = ("model_name", "model")
_UNKNOWN_MODEL = "unknown"
_ERROR_PREVIEW_CHARS = 200


class EmptyLLMResponseError(RuntimeError):
    """The primary model returned no content and no tool call."""


def model_id_of(model: BaseChatModel) -> str:
    """Best-effort model id of a LangChain chat model (for tags and logs)."""
    for attr in _MODEL_NAME_ATTRS:
        value = getattr(model, attr, None)
        if isinstance(value, str) and value:
            return value
    return _UNKNOWN_MODEL


def _is_auth_error(exc: Exception) -> bool:
    return getattr(exc, _STATUS_CODE_ATTR, None) in AUTH_STATUS_CODES


def _is_empty(message: BaseMessage) -> bool:
    if isinstance(message, AIMessage) and message.tool_calls:
        return False
    return not str(message.content).strip()


def _fallback_reason(exc: Exception) -> str:
    if isinstance(exc, TimeoutError):
        return FALLBACK_REASON_TIMEOUT
    if isinstance(exc, EmptyLLMResponseError):
        return FALLBACK_REASON_EMPTY
    return FALLBACK_REASON_ERROR


class RoutedChatModel(BaseChatModel):
    """Primary model of one role, with a timeout and a fallback model."""

    primary: BaseChatModel
    fallback: BaseChatModel | None = None
    role: str
    timeout_seconds: float
    is_fallback: bool = False

    @property
    def _llm_type(self) -> str:
        return _LLM_TYPE

    @property
    def model_name(self) -> str:
        """The primary model id (what normally runs for this role)."""
        return model_id_of(self.primary)

    def as_fallback(self) -> RoutedChatModel | None:
        """The fallback model alone, tagged as a fallback; None when unset."""
        if self.fallback is None:
            return None
        return RoutedChatModel(
            primary=self.fallback,
            role=self.role,
            timeout_seconds=LLM_TIMEOUT_FALLBACK_SECONDS,
            is_fallback=True,
        )

    def _run_config(self, model: BaseChatModel, *, fallback: bool) -> RunnableConfig:
        model_id = model_id_of(model)
        tags = [
            f"{LLM_TAG_ROLE_PREFIX}{self.role}",
            f"{LLM_TAG_MODEL_PREFIX}{model_id}",
        ]
        if fallback:
            tags.append(LLM_TAG_FALLBACK)
        return {
            "tags": tags,
            "metadata": {
                LLM_METADATA_ROLE: self.role,
                LLM_METADATA_MODEL: model_id,
                LLM_METADATA_FALLBACK: fallback,
            },
        }

    async def _call(
        self,
        model: BaseChatModel,
        request: _RoutedRequest,
        timeout: float,
    ) -> AIMessage:
        fallback = request.fallback or self.is_fallback
        config = merge_configs(
            request.config, self._run_config(model, fallback=fallback)
        )
        message = await asyncio.wait_for(
            model.ainvoke(request.prompt, config, stop=request.stop, **request.kwargs),
            timeout,
        )
        # Empty content only triggers the fallback; a fallback's own empty answer
        # is returned as-is so callers keep their existing empty handling.
        if self.fallback is not None and not fallback and _is_empty(message):
            raise EmptyLLMResponseError(model_id_of(model))
        return message

    async def ainvoke(
        self,
        prompt: LanguageModelInput,
        config: RunnableConfig | None = None,
        *,
        stop: list[str] | None = None,
        **kwargs: object,
    ) -> AIMessage:
        """Run the primary model; on failure re-issue the call on the fallback."""
        request = _RoutedRequest(prompt=prompt, config=config, stop=stop, kwargs=kwargs)
        try:
            return await self._call(self.primary, request, self.timeout_seconds)
        except Exception as exc:
            if self.fallback is None or _is_auth_error(exc):
                raise
            logger.warning(
                LOG_LLM_FALLBACK_USED,
                role=self.role,
                primary_model=model_id_of(self.primary),
                fallback_model=model_id_of(self.fallback),
                reason=_fallback_reason(exc),
                error=str(exc)[:_ERROR_PREVIEW_CHARS],
            )
        fallback_request = _RoutedRequest(
            prompt=prompt, config=config, stop=stop, kwargs=kwargs, fallback=True
        )
        return await self._call(
            self.fallback, fallback_request, LLM_TIMEOUT_FALLBACK_SECONDS
        )

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: object,
    ) -> ChatResult:
        """Sync path (unused by the carousel pipeline): primary model only."""
        return self.primary._generate(messages, stop, run_manager, **kwargs)


@dataclass(frozen=True)
class _RoutedRequest:
    """One chat call, re-issuable on the fallback model."""

    prompt: LanguageModelInput
    config: RunnableConfig | None
    stop: list[str] | None
    kwargs: dict[str, object]
    fallback: bool = False


def fallback_runnable_for(
    runnable: Runnable[LanguageModelInput, BaseMessage],
) -> Runnable[LanguageModelInput, BaseMessage] | None:
    """The fallback of a routed model (or of a ``.bind``-ing of one), else None.

    Used by the JSON retry policy to re-issue a call whose output never parsed:
    bound sampling kwargs (temperature/max_tokens) are carried over.
    """
    if isinstance(runnable, RoutedChatModel):
        return runnable.as_fallback()
    if not isinstance(runnable, RunnableBinding):
        return None
    bound = runnable.bound
    if not isinstance(bound, RoutedChatModel):
        return None
    fallback = bound.as_fallback()
    if fallback is None:
        return None
    return fallback.bind(**runnable.kwargs).with_config(runnable.config)


__all__ = [
    "EmptyLLMResponseError",
    "RoutedChatModel",
    "fallback_runnable_for",
    "model_id_of",
]
