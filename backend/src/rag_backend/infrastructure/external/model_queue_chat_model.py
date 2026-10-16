"""Queue of chat models behind per-model circuit breakers (AE-0399).

``ModelQueueChatModel`` is a ``BaseChatModel`` so every carousel consumer keeps
its contract. Each call walks the queue in order: a model whose breaker is
open is skipped instantly; the first model that answers wins. On one model:

* ``FATAL`` / ``QUOTA`` failures give up at once (the breaker opens long);
* ``TRANSIENT`` failures retry with backoff and jitter, and the breaker opens
  after its threshold;
* ``THROTTLED`` (429) waits ``Retry-After`` or a short jittered pause a couple
  of times (the debounce), then moves on;
* empty answers (``CONTENT``) are re-rolled, then the call moves on.

When no model answers, ``AllModelsUnavailableError`` names every model's state
and the "all models down" hook fires (Telegram alert, rate-limited).
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from dataclasses import dataclass, field

import structlog
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.config import merge_configs
from pydantic import ConfigDict, Field

from rag_backend.infrastructure.config.llm_queue_constants import (
    ERR_ALL_MODELS_DOWN,
    ERR_EMPTY_QUEUE,
    LOG_ALL_MODELS_DOWN,
    LOG_MODEL_RETRY,
    LOG_MODEL_SKIPPED,
    QUEUE_BACKOFF_BASE_SECONDS,
    QUEUE_BACKOFF_MAX_SECONDS,
    QUEUE_CONTENT_TRIES,
    QUEUE_JITTER_MAX_SECONDS,
    QUEUE_RETRY_AFTER_CAP_SECONDS,
    QUEUE_THROTTLE_MAX_SECONDS,
    QUEUE_THROTTLE_MIN_SECONDS,
    QUEUE_THROTTLE_RETRIES,
    QUEUE_TRANSIENT_TRIES,
)
from rag_backend.infrastructure.config.llm_routing_constants import (
    LLM_METADATA_FALLBACK,
    LLM_METADATA_MODEL,
    LLM_METADATA_ROLE,
    LLM_TAG_FALLBACK,
    LLM_TAG_MODEL_PREFIX,
    LLM_TAG_ROLE_PREFIX,
)
from rag_backend.infrastructure.external.routed_chat_model import model_id_of
from rag_backend.infrastructure.llm.model_breaker import (
    BreakerRegistry,
    EmptyModelAnswerError,
    FailureClass,
    ModelBreaker,
    classify_failure,
    retry_after_seconds,
)

logger = structlog.get_logger(__name__)

_LLM_TYPE = "model-queue"
_ERROR_PREVIEW_CHARS = 200
_GIVE_UP_AT_ONCE = frozenset({FailureClass.FATAL, FailureClass.QUOTA})

AllDownHook = Callable[[str, str], None]
_RANDOM = random.SystemRandom()
_MIN_MODELS_FOR_FALLBACK = 2


class AllModelsUnavailableError(RuntimeError):
    """No model in the queue could answer (each one's state is named)."""


class _GaveUpError(RuntimeError):
    """One model is done for this call; the queue moves on."""


@dataclass
class _Attempts:
    """Per-model attempt counters for one call."""

    transient: int = 0
    throttled: int = 0
    content: int = 0
    last: str = ""


@dataclass(frozen=True)
class _Call:
    """One chat call, re-issuable on every model of the queue."""

    prompt: LanguageModelInput
    config: RunnableConfig | None
    stop: list[str] | None
    kwargs: dict[str, object] = field(default_factory=dict)
    fallback: bool = False


async def _sleep(seconds: float) -> None:
    """Indirection so tests can skip the real waits."""
    await asyncio.sleep(seconds)


def _jitter() -> float:
    return _RANDOM.uniform(0.0, QUEUE_JITTER_MAX_SECONDS)


def _backoff(attempt: int) -> float:
    delay = QUEUE_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
    return float(min(delay, QUEUE_BACKOFF_MAX_SECONDS)) + _jitter()


def _throttle_wait(exc: BaseException) -> float:
    retry_after = retry_after_seconds(exc)
    if retry_after is not None:
        return float(min(retry_after, QUEUE_RETRY_AFTER_CAP_SECONDS))
    return _RANDOM.uniform(QUEUE_THROTTLE_MIN_SECONDS, QUEUE_THROTTLE_MAX_SECONDS)


def _is_empty(message: BaseMessage) -> bool:
    if isinstance(message, AIMessage) and message.tool_calls:
        return False
    return not str(message.content).strip()


class ModelQueueChatModel(BaseChatModel):
    """The models of one role, tried in order behind their breakers."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    models: list[BaseChatModel] = Field(min_length=1)
    role: str
    timeout_seconds: float
    registry: BreakerRegistry
    on_all_down: AllDownHook | None = None

    @property
    def _llm_type(self) -> str:
        return _LLM_TYPE

    @property
    def model_name(self) -> str:
        """The first model's id (what normally answers for this role)."""
        return model_id_of(self.models[0]) if self.models else ERR_EMPTY_QUEUE

    def as_fallback(self) -> ModelQueueChatModel | None:
        """The rest of the queue, for a call whose JSON never parsed; None at the end."""
        if len(self.models) < _MIN_MODELS_FOR_FALLBACK:
            return None
        return self.model_copy(update={"models": self.models[1:]})

    async def ainvoke(
        self,
        prompt: LanguageModelInput,
        config: RunnableConfig | None = None,
        *,
        stop: list[str] | None = None,
        **kwargs: object,
    ) -> AIMessage:
        """The first answer from the queue; every model's state when none."""
        states: list[str] = []
        for index, model in enumerate(self.models):
            call = _Call(prompt, config, stop, dict(kwargs), fallback=index > 0)
            answer = await self._try_model(model, call, states)
            if answer is not None:
                return answer
        raise self._all_down("; ".join(states))

    async def _try_model(
        self, model: BaseChatModel, call: _Call, states: list[str]
    ) -> AIMessage | None:
        key = model_id_of(model)
        breaker = self.registry.get(key)
        if not breaker.try_acquire():
            logger.info(
                LOG_MODEL_SKIPPED, role=self.role, model=key, state=breaker.describe()
            )
            states.append(f"{key}={breaker.describe()}")
            return None
        try:
            return await self._on_model(model, breaker, call)
        except _GaveUpError as gave_up:
            states.append(f"{key}={breaker.describe()}:{gave_up}")
            return None

    async def _on_model(
        self, model: BaseChatModel, breaker: ModelBreaker, call: _Call
    ) -> AIMessage:
        attempts = _Attempts()
        while True:
            try:
                message = await self._call(model, call)
            except Exception as exc:
                await self._after_failure(breaker, attempts, exc)
                continue
            breaker.record_success()
            return message

    async def _call(self, model: BaseChatModel, call: _Call) -> AIMessage:
        config = merge_configs(
            call.config, self._run_config(model, fallback=call.fallback)
        )
        message = await asyncio.wait_for(
            model.ainvoke(call.prompt, config, stop=call.stop, **call.kwargs),
            self.timeout_seconds,
        )
        if _is_empty(message):
            raise EmptyModelAnswerError(model_id_of(model))
        if isinstance(message, AIMessage):
            return message
        return AIMessage(content=message.content)

    async def _after_failure(
        self, breaker: ModelBreaker, attempts: _Attempts, exc: Exception
    ) -> None:
        """Wait before the next try on this model, or give up on it."""
        failure = classify_failure(exc)
        attempts.last = f"{failure.value}: {str(exc)[:_ERROR_PREVIEW_CHARS]}"
        if failure in _GIVE_UP_AT_ONCE:
            breaker.record_failure(failure, attempts.last)
            raise _GaveUpError(failure.value) from exc
        wait = _retry_wait(failure, attempts, exc)
        if wait is None:
            _record_final(breaker, failure, attempts.last)
            raise _GaveUpError(failure.value) from exc
        if failure is FailureClass.TRANSIENT:
            breaker.record_failure(failure, attempts.last)
            if not breaker.try_acquire():
                raise _GaveUpError(breaker.describe()) from exc
        logger.warning(
            LOG_MODEL_RETRY,
            role=self.role,
            model=breaker.model,
            failure=failure.value,
            wait=round(wait, 2),
        )
        await _sleep(wait)

    def _run_config(self, model: BaseChatModel, *, fallback: bool) -> RunnableConfig:
        model_id = model_id_of(model)
        tags = [
            f"{LLM_TAG_ROLE_PREFIX}{self.role}",
            f"{LLM_TAG_MODEL_PREFIX}{model_id}",
        ]
        if fallback:
            tags.append(LLM_TAG_FALLBACK)
        metadata = {
            LLM_METADATA_ROLE: self.role,
            LLM_METADATA_MODEL: model_id,
            LLM_METADATA_FALLBACK: fallback,
        }
        return {"tags": tags, "metadata": metadata}

    def _all_down(self, summary: str) -> AllModelsUnavailableError:
        logger.error(LOG_ALL_MODELS_DOWN, role=self.role, summary=summary)
        if self.on_all_down is not None:
            self.on_all_down(self.role, summary)
        return AllModelsUnavailableError(ERR_ALL_MODELS_DOWN.format(summary=summary))

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: object,
    ) -> ChatResult:
        """Sync path (unused by the carousel pipeline): first model only."""
        return self.models[0]._generate(messages, stop, run_manager, **kwargs)


def _retry_wait(
    failure: FailureClass, attempts: _Attempts, exc: Exception
) -> float | None:
    """Seconds to wait before retrying this model, or None to move on."""
    if failure is FailureClass.THROTTLED:
        attempts.throttled += 1
        return (
            _throttle_wait(exc)
            if attempts.throttled <= QUEUE_THROTTLE_RETRIES
            else None
        )
    if failure is FailureClass.CONTENT:
        attempts.content += 1
        return 0.0 if attempts.content < QUEUE_CONTENT_TRIES else None
    attempts.transient += 1
    return (
        _backoff(attempts.transient)
        if attempts.transient < QUEUE_TRANSIENT_TRIES
        else None
    )


def _record_final(breaker: ModelBreaker, failure: FailureClass, reason: str) -> None:
    """The model's last failure in this call; a throttle counts as transient."""
    if failure is FailureClass.CONTENT:
        breaker.release_probe()
        return
    breaker.record_failure(FailureClass.TRANSIENT, reason)


__all__ = ["AllModelsUnavailableError", "ModelQueueChatModel"]
