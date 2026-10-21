"""The only LLM step of the owner autofix: re-translate untranslated EN.

One call per attempt for the untranslated EN texts only (never the whole
slide), at most ``AUTOFIX_TRANSLATE_ATTEMPTS`` attempts with a timeout each.
An answer that is empty or still Portuguese is dropped, so the current EN text
stays. When every attempt fails, the result says so and nothing is replaced.

The LangChain model, its Langfuse runnable config and the JSON extractor are
injected by the editorial facade (infrastructure), so this module adds no
application -> infrastructure import.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Protocol

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from rag_backend.application.services.carousel.owner_autofix_plan import (
    RetranslateTarget,
)
from rag_backend.application.services.carousel.owner_autofix_text import (
    looks_portuguese,
)
from rag_backend.application.services.carousel_template.prompts import (
    build_autofix_retranslate_prompt,
)
from rag_backend.domain.constants.carousel_autofix import (
    AUTOFIX_JSON_ID_KEY,
    AUTOFIX_JSON_TEXT_KEY,
    AUTOFIX_JSON_TRANSLATIONS_KEY,
    AUTOFIX_TRANSLATE_ATTEMPTS,
    AUTOFIX_TRANSLATE_TIMEOUT_SECONDS,
    LOG_AUTOFIX_TRANSLATE_FAILED,
)

logger = structlog.get_logger()


class EnRetranslator(Protocol):
    """Translate PT source texts to EN, keyed by target id."""

    async def translate(self, targets: tuple[RetranslateTarget, ...]) -> dict[str, str]:
        """One model call. Raises on transport or parse failure."""
        ...


@dataclass(frozen=True)
class LlmRetranslatorConfig:
    """The chat model plus the facade-provided tracing config and JSON parser."""

    llm: BaseChatModel
    parse_json: Callable[[str], object] = json.loads
    runnable_config: RunnableConfig = field(default_factory=lambda: RunnableConfig())


def _translations(data: object) -> dict[str, str]:
    if not isinstance(data, Mapping):
        raise TypeError(AUTOFIX_JSON_TRANSLATIONS_KEY)
    raw = data.get(AUTOFIX_JSON_TRANSLATIONS_KEY)
    if not isinstance(raw, list):
        raise TypeError(AUTOFIX_JSON_TRANSLATIONS_KEY)
    result: dict[str, str] = {}
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        target_id = item.get(AUTOFIX_JSON_ID_KEY)
        text = item.get(AUTOFIX_JSON_TEXT_KEY)
        if isinstance(target_id, str) and isinstance(text, str):
            result[target_id] = text.strip()
    return result


class LlmEnRetranslator:
    """``EnRetranslator`` backed by the editorial chat model."""

    def __init__(self, config: LlmRetranslatorConfig) -> None:
        self._config = config

    async def translate(self, targets: tuple[RetranslateTarget, ...]) -> dict[str, str]:
        """Render the versioned prompt, call the model once, parse the answer."""
        items = [
            {
                AUTOFIX_JSON_ID_KEY: target.target_id,
                AUTOFIX_JSON_TEXT_KEY: target.source,
            }
            for target in targets
        ]
        prompt = build_autofix_retranslate_prompt(json.dumps(items, ensure_ascii=False))
        response = await self._config.llm.ainvoke(
            [HumanMessage(content=prompt)],
            self._config.runnable_config,
        )
        return _translations(self._config.parse_json(str(response.content)))


@dataclass(frozen=True)
class RetranslateResult:
    """Accepted EN texts by target id; ``failed`` when no attempt succeeded."""

    texts: dict[str, str]
    failed: bool
    attempts: int


def _accepted(
    texts: Mapping[str, str], targets: tuple[RetranslateTarget, ...]
) -> dict[str, str]:
    wanted = {target.target_id for target in targets}
    return {
        target_id: text
        for target_id, text in texts.items()
        if target_id in wanted and text and not looks_portuguese(text)
    }


async def _attempt(
    translator: EnRetranslator, targets: tuple[RetranslateTarget, ...]
) -> dict[str, str] | None:
    """Any provider or parse failure keeps the current EN text."""
    try:
        return await asyncio.wait_for(
            translator.translate(targets),
            timeout=AUTOFIX_TRANSLATE_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        logger.warning(LOG_AUTOFIX_TRANSLATE_FAILED, error=type(exc).__name__)
        return None


async def retranslate_bounded(
    translator: EnRetranslator,
    targets: tuple[RetranslateTarget, ...],
) -> RetranslateResult:
    """Translate the targets with a bounded retry; never raises."""
    if not targets:
        return RetranslateResult(texts={}, failed=False, attempts=0)
    for attempt in range(1, AUTOFIX_TRANSLATE_ATTEMPTS + 1):
        texts = await _attempt(translator, targets)
        if texts is not None:
            return RetranslateResult(
                texts=_accepted(texts, targets), failed=False, attempts=attempt
            )
    return RetranslateResult(texts={}, failed=True, attempts=AUTOFIX_TRANSLATE_ATTEMPTS)


__all__ = [
    "EnRetranslator",
    "LlmEnRetranslator",
    "LlmRetranslatorConfig",
    "RetranslateResult",
    "retranslate_bounded",
]
