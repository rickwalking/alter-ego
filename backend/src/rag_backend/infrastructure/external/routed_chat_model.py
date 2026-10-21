"""Role-routed chat model with an automatic fallback model.

``RoutedChatModel`` is a ``BaseChatModel`` so every carousel consumer keeps its
contract (``ainvoke`` / ``bind`` / ``with_config``). It delegates each call to
the primary model of its role under a per-call timeout and, when that call
fails (any error except auth, a timeout, or empty content), re-issues the same
call on the fallback model, logging ``llm_fallback_used``.

Each model gets ``LLM_ATTEMPTS_PER_MODEL`` attempts (exponential
backoff, logged as ``llm_retry``) before the call moves to the fallback, and the
fallback gets the same number before the error surfaces. Auth errors never
retry: the same key would fail the same way.

``ainvoke`` is overridden so the wrapper adds no generation of its own to
Langfuse: the inner model's run is the generation, carrying the actual model
name plus ``role:<role>`` / ``model:<id>`` tags (and ``fallback:true`` on the
fallback). Token usage is therefore counted once.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from typing import Protocol, runtime_checkable

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
    LLM_ATTEMPTS_PER_MODEL,
    LLM_METADATA_FALLBACK,
    LLM_METADATA_MODEL,
    LLM_METADATA_ROLE,
    LLM_RETRY_BACKOFF_BASE_SECONDS,
    LLM_RETRY_BACKOFF_MAX_SECONDS,
    LLM_TAG_FALLBACK,
    LLM_TAG_MODEL_PREFIX,
    LLM_TAG_ROLE_PREFIX,
    LLM_TIMEOUT_FALLBACK_SECONDS,
    LOG_LLM_FALLBACK_USED,
    LOG_LLM_RETRY,
)

logger = structlog.get_logger(__name__)

_LLM_TYPE = "routed-chat-model"
_STATUS_CODE_ATTR = "status_code"
_MODEL_NAME_ATTRS = ("model_name", "model")
_UNKNOWN_MODEL = "unknown"
_ERROR_PREVIEW_CHARS = 200
_ERR_NO_ATTEMPTS = "routed chat model configured with no attempts"


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


def retry_delay(attempt: int) -> float:
    """Seconds to wait after a failed ``attempt`` (1-based), capped."""
    delay = LLM_RETRY_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
    return float(min(delay, LLM_RETRY_BACKOFF_MAX_SECONDS))


async def _sleep(seconds: float) -> None:
    """Indirection so tests can skip the real backoff."""
    await asyncio.sleep(seconds)


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
    attempts: int = LLM_ATTEMPTS_PER_MODEL

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
            attempts=self.attempts,
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
        """Invoke one model under a timeout.

        Empty content triggers the fallback only from a primary call; a fallback's own
        empty answer is returned as-is so callers keep their existing empty handling.
        """
        fallback = request.fallback or self.is_fallback
        config = merge_configs(
            request.config, self._run_config(model, fallback=fallback)
        )
        message = await asyncio.wait_for(
            model.ainvoke(request.prompt, config, stop=request.stop, **request.kwargs),
            timeout,
        )
        if self.fallback is not None and not fallback and _is_empty(message):
            raise EmptyLLMResponseError(model_id_of(model))
        return message

    async def _call_with_retries(
        self,
        model: BaseChatModel,
        request: _RoutedRequest,
        timeout: float,
    ) -> AIMessage:
        """``attempts`` tries on one model; auth errors and the last error raise."""
        for attempt in range(1, self.attempts + 1):
            try:
                return await self._call(model, request, timeout)
            except Exception as exc:
                if _is_auth_error(exc) or attempt == self.attempts:
                    raise
                _log_retry(_RetryNotice(self.role, model, attempt, exc))
                await _sleep(retry_delay(attempt))
        raise RuntimeError(_ERR_NO_ATTEMPTS)

    async def ainvoke(
        self,
        prompt: LanguageModelInput,
        config: RunnableConfig | None = None,
        *,
        stop: list[str] | None = None,
        **kwargs: object,
    ) -> AIMessage:
        """Retry the primary model; then re-issue the call on the fallback."""
        request = _RoutedRequest(prompt=prompt, config=config, stop=stop, kwargs=kwargs)
        try:
            return await self._call_with_retries(
                self.primary, request, self.timeout_seconds
            )
        except Exception as exc:
            if self.fallback is None or _is_auth_error(exc):
                raise
            _log_fallback(self, exc)
        fallback_request = replace(request, fallback=True)
        return await self._call_with_retries(
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
class _RetryNotice:
    """One failed attempt, for the ``llm_retry`` log."""

    role: str
    model: BaseChatModel
    attempt: int
    error: Exception


def _log_retry(notice: _RetryNotice) -> None:
    logger.warning(
        LOG_LLM_RETRY,
        role=notice.role,
        model=model_id_of(notice.model),
        attempt=notice.attempt,
        reason=_fallback_reason(notice.error),
        error=str(notice.error)[:_ERROR_PREVIEW_CHARS],
    )


def _log_fallback(routed: RoutedChatModel, exc: Exception) -> None:
    if routed.fallback is None:
        return
    logger.warning(
        LOG_LLM_FALLBACK_USED,
        role=routed.role,
        primary_model=model_id_of(routed.primary),
        fallback_model=model_id_of(routed.fallback),
        reason=_fallback_reason(exc),
        attempts=routed.attempts,
        error=str(exc)[:_ERROR_PREVIEW_CHARS],
    )


@dataclass(frozen=True)
class _RoutedRequest:
    """One chat call, re-issuable on the fallback model."""

    prompt: LanguageModelInput
    config: RunnableConfig | None
    stop: list[str] | None
    kwargs: dict[str, object]
    fallback: bool = False


@runtime_checkable
class HasFallback(Protocol):
    """A chat model that can hand a call to its fallback."""

    def as_fallback(self) -> BaseChatModel | None:
        """The model to re-issue a call on, or None when there is none."""
        ...


def fallback_runnable_for(
    runnable: Runnable[LanguageModelInput, BaseMessage],
) -> Runnable[LanguageModelInput, BaseMessage] | None:
    """The fallback of a routed model (or of a ``.bind``-ing of one), else None.

    Used by the JSON retry policy to re-issue a call whose output never parsed:
    bound sampling kwargs (temperature/max_tokens) are carried over.
    """
    if isinstance(runnable, HasFallback):
        return runnable.as_fallback()
    if not isinstance(runnable, RunnableBinding):
        return None
    bound = runnable.bound
    if not isinstance(bound, HasFallback):
        return None
    fallback = bound.as_fallback()
    if fallback is None:
        return None
    return fallback.bind(**runnable.kwargs).with_config(runnable.config)


__all__ = [
    "EmptyLLMResponseError",
    "HasFallback",
    "RoutedChatModel",
    "fallback_runnable_for",
    "model_id_of",
]
