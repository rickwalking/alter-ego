"""Prompt ideas for a new cover photo ("Mais ideias"): one fast-queue LLM call.

Pedro's rule: the curated catalogue comes first in the create form; this service
backs "Mais ideias" with prompts tailored to the carousel topic and the slide
palette. Only those two reach the model (no personal data beyond the topic). The
answer is JSON ``{"ideas": [...]}`` and every idea is re-checked here: a string of
``IDEA_MIN_LEN``-``IDEA_MAX_LEN`` characters once whitespace is collapsed, without
markup characters, not repeating another idea. Fewer than ``IDEA_MIN_COUNT`` usable
ideas gets one more call; still fewer, or any LLM failure with nothing kept, raises
:class:`CoverPromptIdeasError`. Nothing is stored.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol

import structlog

from rag_backend.application.services.blog.ai_envelope import strip_code_fence
from rag_backend.domain.constants.cover_prompt_ideas import (
    ERR_COVER_PROMPT_IDEAS_UNAVAILABLE,
    IDEA_ATTEMPTS,
    IDEA_FORBIDDEN_CHARS,
    IDEA_MAX_COUNT,
    IDEA_MAX_LEN,
    IDEA_MIN_COUNT,
    IDEA_MIN_LEN,
    IDEAS_TIMEOUT_SECONDS,
    KEY_IDEAS,
    LOG_COVER_IDEAS_CALL_FAILED,
    NO_PALETTE_HINT,
    IdeaLocale,
)
from rag_backend.domain.constants.palette_types import PaletteMode

logger = structlog.get_logger(__name__)


class CoverIdeasLLM(Protocol):
    """The completion port: the fast chat model with the cap and temperature bound."""

    async def complete(self, prompt: str) -> str: ...


IdeasPromptRenderer = Callable[[str, str, IdeaLocale], str]
IdeasTraceScope = Callable[[str], AbstractContextManager[object]]


class CoverPromptIdeasError(RuntimeError):
    """Not enough ideas could be produced; ``code`` is the API detail."""

    def __init__(self, code: str = ERR_COVER_PROMPT_IDEAS_UNAVAILABLE) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CoverIdeasPorts:
    """The LLM, the prompt renderer (topic, palette line, locale) and the trace."""

    llm: CoverIdeasLLM
    render_prompt: IdeasPromptRenderer
    trace: IdeasTraceScope


@dataclass(frozen=True)
class CoverIdeasPalette:
    """The slide palette the ideas should suit (strict hex, already validated)."""

    name: str
    mode: PaletteMode
    background: str
    primary: str
    accent: str

    def describe(self) -> str:
        """One line for the prompt: name, mode and the three colours."""
        return (
            f"{self.name}: {self.mode.value} background {self.background}, "
            f"primary {self.primary}, accent {self.accent}"
        )


@dataclass(frozen=True)
class CoverIdeasRequest:
    """The carousel topic, its palette (or none), the UI language and the caller."""

    topic: str
    palette: CoverIdeasPalette | None
    locale: IdeaLocale
    user_id: str


def _clean(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    idea = " ".join(raw.split())
    if not IDEA_MIN_LEN <= len(idea) <= IDEA_MAX_LEN:
        return None
    if any(char in idea for char in IDEA_FORBIDDEN_CHARS):
        return None
    return idea


def _add_new(kept: list[str], fresh: list[str]) -> list[str]:
    """``kept`` plus the fresh ideas it does not hold yet (case-insensitive)."""
    merged = list(kept)
    seen = {idea.casefold() for idea in merged}
    for idea in fresh:
        if idea.casefold() not in seen:
            seen.add(idea.casefold())
            merged.append(idea)
    return merged[:IDEA_MAX_COUNT]


def parse_ideas(answer: str) -> list[str]:
    """The usable, distinct ideas of an LLM answer (at most six); [] if unparsable."""
    try:
        data = json.loads(strip_code_fence(answer))
    except json.JSONDecodeError:
        return []
    items = data.get(KEY_IDEAS) if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
    cleaned = [_clean(item) for item in items]
    return _add_new([], [idea for idea in cleaned if idea is not None])


class CoverPromptIdeasService:
    """Turn a topic and a palette into prompt ideas for a new cover photo."""

    def __init__(self, ports: CoverIdeasPorts) -> None:
        self._ports = ports

    async def suggest(self, request: CoverIdeasRequest) -> list[str]:
        """Three to six distinct ideas; raises :class:`CoverPromptIdeasError`."""
        palette = request.palette.describe() if request.palette else NO_PALETTE_HINT
        prompt = self._ports.render_prompt(request.topic, palette, request.locale)
        ideas: list[str] = []
        with self._ports.trace(request.user_id):
            for _ in range(IDEA_ATTEMPTS):
                answer = await self._answer(prompt)
                ideas = _add_new(ideas, parse_ideas(answer))
                if len(ideas) >= IDEA_MIN_COUNT:
                    return ideas
        raise CoverPromptIdeasError

    async def _answer(self, prompt: str) -> str:
        """The model's answer, or "" when it fails or times out (counts as no ideas)."""
        try:
            answer = await asyncio.wait_for(
                self._ports.llm.complete(prompt), timeout=IDEAS_TIMEOUT_SECONDS
            )
        except Exception as exc:
            logger.warning(LOG_COVER_IDEAS_CALL_FAILED, error=type(exc).__name__)
            return ""
        return answer or ""


__all__ = [
    "CoverIdeasLLM",
    "CoverIdeasPalette",
    "CoverIdeasPorts",
    "CoverIdeasRequest",
    "CoverPromptIdeasError",
    "CoverPromptIdeasService",
    "parse_ideas",
]
