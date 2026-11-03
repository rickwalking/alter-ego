"""The model side of the shorten step: request, port and fast-model adapter.

One call per attempt carries every field still over its limit (id, slide,
locale, path, current text, problems, slide heading, limit, PT source for EN
fields) and the author's style guide. The answer is the gate repair's
``{"fixes": [{"id", "text"}]}`` shape, parsed by the same parser. The chat
model, the role's fallback model and the Langfuse runnable config are injected
by the orchestrator, so this module adds no application -> infrastructure
import.

Deadline order: the step bounds one attempt at ``COPY_BUDGET_FIT_TIMEOUT_SECONDS``
while the fast role waits up to 300 s per call (several tries) before its own
queue reaches the fallback, so a slow primary was cancelled before the fallback
ever ran. With a fallback configured, the primary gets
``COPY_BUDGET_FIT_PRIMARY_SECONDS``; a primary that times out or answers
unparseable JSON hands the same prompt to the fallback, which runs in what is
left of the attempt. Any other failure already went through the role's whole
queue and is raised as it is.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Protocol

import structlog
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import Runnable, RunnableConfig

from rag_backend.application.services.carousel.content_gate_repair import parse_fixes
from rag_backend.application.services.carousel.content_gate_repair_targets import (
    FieldRepairTarget,
)
from rag_backend.application.services.carousel.copy_budget_limits import FieldLimit
from rag_backend.application.services.carousel_template.prompts import (
    build_copy_budget_fit_prompt,
)
from rag_backend.domain.constants.content_gate_repair import (
    GATE_REPAIR_FIELD_LOCALE,
    GATE_REPAIR_FIELD_PATH,
    GATE_REPAIR_FIELD_PROBLEMS,
    GATE_REPAIR_FIELD_PT_TEXT,
    GATE_REPAIR_FIELD_SLIDE,
    GATE_REPAIR_FIELD_SLIDE_HEADING,
    GATE_REPAIR_FIELD_TEXT,
    GATE_REPAIR_JSON_ID_KEY,
)
from rag_backend.domain.constants.copy_budget_fit import (
    BINDABLE_MODEL_KEYS,
    COPY_BUDGET_FIT_PRIMARY_SECONDS,
    COPY_BUDGET_VAR_FIELDS_JSON,
    COPY_BUDGET_VAR_STYLE_GUIDE,
    LIMIT_KEY_FIELD,
    LOG_COPY_BUDGET_FIT_FALLBACK_USED,
)

logger = structlog.get_logger(__name__)

ChatRunnable = Runnable[LanguageModelInput, BaseMessage]

_FALLBACK_ON: tuple[type[Exception], ...] = (TimeoutError, ValueError, TypeError)


@dataclass(frozen=True)
class FitTarget:
    """One over-budget field and the full limit it must fit."""

    target: FieldRepairTarget
    limit: FieldLimit


@dataclass(frozen=True)
class FitRequest:
    """One attempt: the over-budget fields and the author's style guide."""

    targets: tuple[FitTarget, ...]
    style_guide: str = ""


class CopyBudgetFitter(Protocol):
    """Rewrite the requested fields within their limits; answers keyed by id."""

    async def fit(self, request: FitRequest) -> dict[str, str]:
        """One model call. May raise on transport or parse failure."""
        ...


def _empty_config() -> RunnableConfig:
    return RunnableConfig()


@dataclass(frozen=True)
class LlmCopyBudgetConfig:
    """The fast chat model, its fallback and the orchestrator-provided tracing.

    ``primary_seconds`` is the primary's window when ``fallback`` is set; without
    a fallback the primary keeps the whole attempt.
    """

    llm: BaseChatModel
    runnable_config: Callable[[], RunnableConfig] = field(default=_empty_config)
    fallback: ChatRunnable | None = None
    primary_seconds: float = COPY_BUDGET_FIT_PRIMARY_SECONDS


def _field_json(item: FitTarget) -> dict[str, object]:
    target = item.target
    entry: dict[str, object] = {
        GATE_REPAIR_JSON_ID_KEY: target.target_id,
        GATE_REPAIR_FIELD_SLIDE: target.slide_index,
        GATE_REPAIR_FIELD_LOCALE: target.locale,
        GATE_REPAIR_FIELD_PATH: target.field,
        GATE_REPAIR_FIELD_TEXT: target.text,
        GATE_REPAIR_FIELD_PROBLEMS: list(target.problems),
        GATE_REPAIR_FIELD_SLIDE_HEADING: target.slide_heading,
    }
    if target.source_text:
        entry[GATE_REPAIR_FIELD_PT_TEXT] = target.source_text
    limit = item.limit.as_dict()
    limit.pop(LIMIT_KEY_FIELD, None)
    entry.update(limit)
    return entry


def render_fit_prompt(request: FitRequest) -> tuple[str, dict[str, object]]:
    """The versioned shorten prompt for one attempt and its YAML model config."""
    fields = [_field_json(item) for item in request.targets]
    return build_copy_budget_fit_prompt({
        COPY_BUDGET_VAR_FIELDS_JSON: json.dumps(fields, ensure_ascii=False, indent=2),
        COPY_BUDGET_VAR_STYLE_GUIDE: request.style_guide,
    })


def model_bind_kwargs(model_cfg: Mapping[str, object]) -> dict[str, object]:
    """The numeric ``temperature`` / ``max_tokens`` of the prompt's model block."""
    bind: dict[str, object] = {}
    for key in BINDABLE_MODEL_KEYS:
        value = model_cfg.get(key)
        if isinstance(value, int | float) and not isinstance(value, bool):
            bind[key] = value
    return bind


class LlmCopyBudgetFitter:
    """``CopyBudgetFitter`` backed by the fast chat model."""

    def __init__(self, config: LlmCopyBudgetConfig) -> None:
        self._config = config

    async def fit(self, request: FitRequest) -> dict[str, str]:
        """Render the prompt and ask the primary, then the fallback if it fails.

        The YAML's ``temperature`` and ``max_tokens`` are bound per call, as the
        content drafter does, so the prompt file controls the sampling. Both
        calls carry the same Langfuse runnable config.
        """
        prompt, model_cfg = render_fit_prompt(request)
        call = _Call(prompt, model_bind_kwargs(model_cfg))
        fallback = self._config.fallback
        if fallback is None:
            return await self._ask(self._config.llm, call)
        try:
            return await asyncio.wait_for(
                self._ask(self._config.llm, call), self._config.primary_seconds
            )
        except _FALLBACK_ON as exc:
            logger.warning(LOG_COPY_BUDGET_FIT_FALLBACK_USED, reason=type(exc).__name__)
        return await self._ask(fallback, call)

    async def _ask(self, model: ChatRunnable, call: _Call) -> dict[str, str]:
        """One call on ``model`` with the prompt's sampling bound, parsed."""
        runnable = model.bind(**call.bind) if call.bind else model
        response = await runnable.ainvoke(
            [HumanMessage(content=call.prompt)], self._config.runnable_config()
        )
        return parse_fixes(str(response.content))


@dataclass(frozen=True)
class _Call:
    """The rendered prompt and the sampling kwargs bound on every model."""

    prompt: str
    bind: dict[str, object]


__all__ = [
    "ChatRunnable",
    "CopyBudgetFitter",
    "FitRequest",
    "FitTarget",
    "LlmCopyBudgetConfig",
    "LlmCopyBudgetFitter",
    "model_bind_kwargs",
    "render_fit_prompt",
]
