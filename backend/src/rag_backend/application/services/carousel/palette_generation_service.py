"""Create a palette with AI: a fast-queue LLM call, up to three candidates.

The owner's description goes to the versioned prompt (injected
``render_prompt``, ``agents/prompts/palette/v1/generate.yaml``) and the fast LLM
answers JSON through the injected completion, which carries the token cap and
temperature. Every candidate is re-validated here, never trusted: strict hex,
the palette name rules (trimmed, no angle brackets, cut to the column length),
keywords lower-cased, de-duplicated, capped and without root brand keywords (a
missing or malformed keyword list is empty). The mode follows the background
luminance, and every colour pair is brought to WCAG AA by
:mod:`palette_contrast`. Candidates repeating a name or a colour set are
dropped. When fewer than three are valid the model is asked once more and the
new ones are added. Nothing is stored: the candidates only pre-fill the create
form. Any LLM failure, or no valid candidate after both answers, raises
:class:`PaletteGenerationError`.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol

from rag_backend.application.services.blog.ai_envelope import strip_code_fence
from rag_backend.application.services.carousel.palette_contrast import (
    contrast_ratio,
    repair_against,
    repair_background,
    slide_ink,
)
from rag_backend.application.services.carousel_template.theme_mode import (
    is_light_background,
)
from rag_backend.domain.constants.carousel_themes import BRAND_KEYWORDS
from rag_backend.domain.constants.palette_catalog import (
    HEX_COLOUR_RE,
    KEYWORD_MAX_COUNT,
    KEYWORD_MAX_LEN,
    NAME_FORBIDDEN_CHARS,
    NAME_MAX_LEN,
)
from rag_backend.domain.constants.palette_generation import (
    CONTRAST_DECIMALS,
    ERR_PALETTE_GENERATION_UNAVAILABLE,
    GENERATION_ATTEMPTS,
    GENERATION_TIMEOUT_SECONDS,
    KEY_ACCENT,
    KEY_BACKGROUND,
    KEY_CANDIDATES,
    KEY_KEYWORDS,
    KEY_NAME,
    KEY_PRIMARY,
    PALETTE_CANDIDATE_COUNT,
)
from rag_backend.domain.constants.palette_types import PaletteMode

_BRAND_KEYWORDS: frozenset[str] = frozenset(
    keyword.lower() for keywords in BRAND_KEYWORDS.values() for keyword in keywords
)


class PaletteGenerationLLM(Protocol):
    """The completion port: the fast chat model with the cap and temperature bound."""

    async def complete(self, prompt: str) -> str: ...


PromptRenderer = Callable[[str], str]
TraceScope = Callable[[str], AbstractContextManager[object]]


class PaletteGenerationError(RuntimeError):
    """No candidate could be produced; ``code`` is the API detail."""

    def __init__(self, code: str = ERR_PALETTE_GENERATION_UNAVAILABLE) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class PaletteGenerationPorts:
    """The LLM, the prompt renderer and the Langfuse trace scope (by user id)."""

    llm: PaletteGenerationLLM
    render_prompt: PromptRenderer
    trace: TraceScope


@dataclass(frozen=True)
class PaletteGenerationRequest:
    """The owner's description and who asked (for the trace)."""

    description: str
    user_id: str


@dataclass(frozen=True)
class PaletteContrast:
    """Contrast ratios against the background: slide ink, primary, accent."""

    text: float
    primary: float
    accent: float


@dataclass(frozen=True)
class PaletteCandidate:
    """One validated, AA-checked palette suggestion (not stored)."""

    name: str
    primary: str
    accent: str
    background: str
    mode: PaletteMode
    keywords: tuple[str, ...]
    contrast: PaletteContrast


def _hex(value: object) -> str | None:
    if not isinstance(value, str) or HEX_COLOUR_RE.match(value.strip()) is None:
        return None
    return value.strip().lower()


def _name(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    name = value.strip()[:NAME_MAX_LEN].strip()
    if not name or any(char in name for char in NAME_FORBIDDEN_CHARS):
        return None
    return name


def _keywords(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    cleaned: list[str] = []
    for raw in value:
        keyword = raw.strip().lower() if isinstance(raw, str) else ""
        usable = keyword and len(keyword) <= KEYWORD_MAX_LEN
        if usable and keyword not in _BRAND_KEYWORDS and keyword not in cleaned:
            cleaned.append(keyword)
    return tuple(cleaned[:KEYWORD_MAX_COUNT])


def _ratio(first: str, second: str) -> float:
    return round(contrast_ratio(first, second), CONTRAST_DECIMALS)


def _candidate(raw: object) -> PaletteCandidate | None:
    if not isinstance(raw, dict):
        return None
    name = _name(raw.get(KEY_NAME))
    colours = [_hex(raw.get(key)) for key in (KEY_PRIMARY, KEY_ACCENT, KEY_BACKGROUND)]
    keywords = _keywords(raw.get(KEY_KEYWORDS, []))
    primary, accent, background = colours
    if name is None or not (primary and accent and background):
        return None
    background = repair_background(background)
    primary = repair_against(primary, background)
    accent = repair_against(accent, background)
    light = is_light_background(background)
    return PaletteCandidate(
        name=name,
        primary=primary,
        accent=accent,
        background=background,
        mode=PaletteMode.LIGHT if light else PaletteMode.DARK,
        keywords=keywords,
        contrast=PaletteContrast(
            text=_ratio(slide_ink(background), background),
            primary=_ratio(primary, background),
            accent=_ratio(accent, background),
        ),
    )


def _raw_candidates(answer: str) -> list[object]:
    try:
        data = json.loads(strip_code_fence(answer))
    except json.JSONDecodeError as exc:
        raise PaletteGenerationError from exc
    items = data.get(KEY_CANDIDATES) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise PaletteGenerationError
    return items


def _colours(candidate: PaletteCandidate) -> tuple[str, str, str]:
    return candidate.primary, candidate.accent, candidate.background


def _merge(
    kept: list[PaletteCandidate], new: list[PaletteCandidate]
) -> list[PaletteCandidate]:
    """``kept`` plus the new candidates whose name and colours are not taken yet."""
    merged = list(kept)
    for candidate in new:
        names = {other.name.casefold() for other in merged}
        colours = {_colours(other) for other in merged}
        if candidate.name.casefold() in names or _colours(candidate) in colours:
            continue
        merged.append(candidate)
    return merged[:PALETTE_CANDIDATE_COUNT]


def parse_candidates(answer: str) -> list[PaletteCandidate]:
    """The valid, repaired, distinct candidates of an LLM answer (at most three)."""
    try:
        items = _raw_candidates(answer)
    except PaletteGenerationError:
        return []
    parsed = (_candidate(item) for item in items)
    return _merge([], [candidate for candidate in parsed if candidate is not None])


class PaletteGenerationService:
    """Turn a description into AA-checked palette candidates (nothing stored)."""

    def __init__(self, ports: PaletteGenerationPorts) -> None:
        self._ports = ports

    async def generate(
        self, request: PaletteGenerationRequest
    ) -> list[PaletteCandidate]:
        """Up to three distinct candidates; raises :class:`PaletteGenerationError`.

        Fewer than three valid candidates in the first answer → one more call;
        a failing second call keeps the first call's candidates.
        """
        prompt = self._ports.render_prompt(request.description)
        candidates: list[PaletteCandidate] = []
        with self._ports.trace(request.user_id):
            for _ in range(GENERATION_ATTEMPTS):
                try:
                    answer = await self._complete(prompt)
                except PaletteGenerationError:
                    if candidates:
                        break
                    raise
                candidates = _merge(candidates, parse_candidates(answer))
                if len(candidates) == PALETTE_CANDIDATE_COUNT:
                    break
        if not candidates:
            raise PaletteGenerationError
        return candidates

    async def _complete(self, prompt: str) -> str:
        try:
            answer = await asyncio.wait_for(
                self._ports.llm.complete(prompt), timeout=GENERATION_TIMEOUT_SECONDS
            )
        except Exception as exc:
            raise PaletteGenerationError from exc
        return answer or ""


__all__ = [
    "PaletteCandidate",
    "PaletteContrast",
    "PaletteGenerationError",
    "PaletteGenerationLLM",
    "PaletteGenerationPorts",
    "PaletteGenerationRequest",
    "PaletteGenerationService",
    "parse_candidates",
]
