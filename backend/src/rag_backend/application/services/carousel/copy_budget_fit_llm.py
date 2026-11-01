"""The model side of the shorten step: request, port and fast-model adapter.

One call per attempt carries every field still over its limit (id, slide,
locale, path, current text, problems, slide heading, limit, PT source for EN
fields) and the author's style guide. The answer is the gate repair's
``{"fixes": [{"id", "text"}]}`` shape, parsed by the same parser. The chat
model and its Langfuse runnable config are injected by the orchestrator, so
this module adds no application -> infrastructure import.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

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
    COPY_BUDGET_VAR_FIELDS_JSON,
    COPY_BUDGET_VAR_STYLE_GUIDE,
    LIMIT_KEY_FIELD,
)


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
    """The fast chat model plus the orchestrator-provided tracing config."""

    llm: BaseChatModel
    runnable_config: Callable[[], RunnableConfig] = field(default=_empty_config)


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


def render_fit_prompt(request: FitRequest) -> str:
    """The versioned shorten prompt for one attempt."""
    fields = [_field_json(item) for item in request.targets]
    return build_copy_budget_fit_prompt({
        COPY_BUDGET_VAR_FIELDS_JSON: json.dumps(fields, ensure_ascii=False, indent=2),
        COPY_BUDGET_VAR_STYLE_GUIDE: request.style_guide,
    })


class LlmCopyBudgetFitter:
    """``CopyBudgetFitter`` backed by the fast chat model."""

    def __init__(self, config: LlmCopyBudgetConfig) -> None:
        self._config = config

    async def fit(self, request: FitRequest) -> dict[str, str]:
        """Render the prompt, call the model once, parse the answer."""
        response = await self._config.llm.ainvoke(
            [HumanMessage(content=render_fit_prompt(request))],
            self._config.runnable_config(),
        )
        return parse_fixes(str(response.content))


__all__ = [
    "CopyBudgetFitter",
    "FitRequest",
    "FitTarget",
    "LlmCopyBudgetConfig",
    "LlmCopyBudgetFitter",
    "render_fit_prompt",
]
