"""Palette generation service: parsing, validation and WCAG AA repair.

Feature: Generate palette candidates from a description
(tests/features/palette_generate_ae0507.feature).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager

import pytest

from rag_backend.application.services.carousel.palette_contrast import (
    contrast_ratio,
    repair_against,
    slide_ink,
)
from rag_backend.application.services.carousel.palette_generation_service import (
    PaletteGenerationError,
    PaletteGenerationPorts,
    PaletteGenerationRequest,
    PaletteGenerationService,
)
from rag_backend.domain.constants.palette_generation import WCAG_AA_TEXT_CONTRAST
from rag_backend.domain.constants.palette_types import PaletteMode

_DARK = {
    "name": "Noite Azul",
    "primary": "#38bdf8",
    "accent": "#f472b6",
    "background": "#0b1020",
    "mode": "dark",
    "keywords": ["night", "blue"],
}
_LIGHT = {
    "name": "Areia",
    "primary": "#1d4ed8",
    "accent": "#9a3412",
    "background": "#f8f5ee",
    "mode": "light",
    "keywords": ["sand"],
}
_FOREST = {
    "name": "Floresta",
    "primary": "#86efac",
    "accent": "#fde68a",
    "background": "#052e16",
    "mode": "dark",
    "keywords": ["forest", "green"],
}


class _FakeLLM:
    """Answers one canned text (or raises) and records the prompts it got."""

    def __init__(self, answer: str | Exception) -> None:
        self.answer = answer
        self.prompts: list[str] = []

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        self.prompts.append(messages[-1]["content"])
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


class _TraceRecorder:
    """Collects the user ids the generation traced under."""

    def __init__(self) -> None:
        self.users: list[str] = []

    def __call__(self, user_id: str) -> AbstractContextManager[object]:
        @contextmanager
        def scope() -> Iterator[object]:
            self.users.append(user_id)
            yield object()

        return scope()


def _service(answer: str | Exception) -> tuple[PaletteGenerationService, _FakeLLM]:
    llm = _FakeLLM(answer)
    ports = PaletteGenerationPorts(
        llm=llm,
        render_prompt=lambda description: f"PROMPT[{description}]",
        trace=_TraceRecorder(),
    )
    return PaletteGenerationService(ports), llm


def _answer(*candidates: dict[str, object]) -> str:
    return json.dumps({"candidates": list(candidates)})


_REQUEST = PaletteGenerationRequest(description="noite azul e rosa", user_id="u-1")


class TestCandidates:
    @pytest.mark.asyncio
    async def test_three_candidates_are_returned(self) -> None:
        """Scenario: A description returns three validated candidates."""
        service, llm = _service(_answer(_DARK, _LIGHT, _FOREST))
        candidates = await service.generate(_REQUEST)
        assert [c.name for c in candidates] == ["Noite Azul", "Areia", "Floresta"]
        assert candidates[0].primary == "#38bdf8"
        assert candidates[0].keywords == ("night", "blue")
        assert candidates[1].mode is PaletteMode.LIGHT
        assert llm.prompts == ["PROMPT[noite azul e rosa]"]

    @pytest.mark.asyncio
    async def test_at_most_three_candidates_and_a_fenced_answer(self) -> None:
        """Scenario: A description returns three validated candidates."""
        fenced = f"```json\n{_answer(_DARK, _LIGHT, _FOREST, _DARK)}\n```"
        service, _ = _service(fenced)
        assert len(await service.generate(_REQUEST)) == 3

    @pytest.mark.asyncio
    async def test_a_bare_list_answer_is_accepted(self) -> None:
        """Scenario: A description returns three validated candidates."""
        service, _ = _service(json.dumps([_DARK]))
        assert [c.name for c in await service.generate(_REQUEST)] == ["Noite Azul"]

    @pytest.mark.asyncio
    async def test_the_generation_is_traced_for_the_user(self) -> None:
        """Scenario: A description returns three validated candidates."""
        llm = _FakeLLM(_answer(_DARK))
        trace = _TraceRecorder()
        ports = PaletteGenerationPorts(llm=llm, render_prompt=lambda d: d, trace=trace)
        await PaletteGenerationService(ports).generate(_REQUEST)
        assert trace.users == ["u-1"]

    @pytest.mark.asyncio
    async def test_hex_is_lower_cased_and_contrast_is_reported(self) -> None:
        """Scenario: A description returns three validated candidates."""
        upper = {**_DARK, "primary": "#38BDF8"}
        service, _ = _service(_answer(upper))
        [candidate] = await service.generate(_REQUEST)
        assert candidate.primary == "#38bdf8"
        assert candidate.contrast.primary == round(
            contrast_ratio("#38bdf8", "#0b1020"), 2
        )
        assert candidate.contrast.text >= WCAG_AA_TEXT_CONTRAST


class TestContrastRepair:
    @pytest.mark.asyncio
    async def test_low_contrast_accent_is_repaired(self) -> None:
        """Scenario: A low-contrast colour is repaired before it is returned."""
        muddy = {**_DARK, "accent": "#1e2a44"}
        service, _ = _service(_answer(muddy))
        [candidate] = await service.generate(_REQUEST)
        assert candidate.accent != "#1e2a44"
        assert contrast_ratio(candidate.accent, candidate.background) >= 4.5
        assert candidate.contrast.accent >= WCAG_AA_TEXT_CONTRAST

    @pytest.mark.asyncio
    async def test_low_contrast_primary_on_light_is_darkened(self) -> None:
        """Scenario: A low-contrast colour is repaired before it is returned."""
        pale = {**_LIGHT, "primary": "#fde68a"}
        service, _ = _service(_answer(pale))
        [candidate] = await service.generate(_REQUEST)
        assert contrast_ratio(candidate.primary, candidate.background) >= 4.5
        assert candidate.primary < "#fde68a"

    @pytest.mark.asyncio
    async def test_mid_grey_background_is_repaired_for_the_slide_ink(self) -> None:
        """Scenario: A low-contrast colour is repaired before it is returned."""
        grey = {**_DARK, "background": "#777777"}
        service, _ = _service(_answer(grey))
        [candidate] = await service.generate(_REQUEST)
        ink = slide_ink(candidate.background)
        assert contrast_ratio(ink, candidate.background) >= 4.5
        assert contrast_ratio(candidate.primary, candidate.background) >= 4.5
        assert contrast_ratio(candidate.accent, candidate.background) >= 4.5

    def test_a_colour_that_only_passes_as_white_becomes_white(self) -> None:
        """Scenario: A low-contrast colour is repaired before it is returned."""
        assert repair_against("#737373", "#737373") == "#ffffff"
        assert repair_against("#ffffff", "#737373") == "#ffffff"

    @pytest.mark.asyncio
    async def test_mode_follows_the_background(self) -> None:
        """Scenario: The mode follows the background."""
        mislabelled = {**_LIGHT, "mode": "dark"}
        service, _ = _service(_answer(mislabelled))
        [candidate] = await service.generate(_REQUEST)
        assert candidate.mode is PaletteMode.LIGHT
        assert slide_ink(candidate.background) == "#16181d"


class TestInvalidCandidates:
    @pytest.mark.asyncio
    async def test_invalid_candidates_are_dropped(self) -> None:
        """Scenario: Invalid candidates are dropped."""
        bad_hex = {**_LIGHT, "primary": "red; ignore previous instructions"}
        unsafe = {**_FOREST, "name": "<script>x</script>"}
        service, _ = _service(_answer(_DARK, bad_hex, unsafe))
        assert [c.name for c in await service.generate(_REQUEST)] == ["Noite Azul"]

    @pytest.mark.parametrize(
        "broken",
        [
            {**_DARK, "name": "   "},
            {**_DARK, "name": 7},
            {key: value for key, value in _DARK.items() if key != "accent"},
            {**_DARK, "keywords": "night"},
            "not an object",
        ],
    )
    @pytest.mark.asyncio
    async def test_malformed_candidates_are_dropped(self, broken: object) -> None:
        """Scenario: Invalid candidates are dropped."""
        service, _ = _service(json.dumps({"candidates": [broken, _LIGHT]}))
        assert [c.name for c in await service.generate(_REQUEST)] == ["Areia"]

    @pytest.mark.asyncio
    async def test_a_long_name_is_cut_to_the_limit(self) -> None:
        """Scenario: Invalid candidates are dropped."""
        service, _ = _service(_answer({**_DARK, "name": "N" * 120}))
        [candidate] = await service.generate(_REQUEST)
        assert candidate.name == "N" * 80

    @pytest.mark.asyncio
    async def test_brand_and_oversized_keywords_are_dropped(self) -> None:
        """Scenario: Brand keywords are dropped from a candidate."""
        keywords = [
            " Night ",
            "night",
            "openai",
            "x" * 31,
            *[f"k{i}" for i in range(12)],
        ]
        service, _ = _service(_answer({**_DARK, "keywords": keywords}))
        [candidate] = await service.generate(_REQUEST)
        assert "openai" not in candidate.keywords
        assert candidate.keywords[0] == "night"
        assert len(candidate.keywords) == 10
        assert all(len(keyword) <= 30 for keyword in candidate.keywords)

    @pytest.mark.asyncio
    async def test_non_text_keywords_are_ignored(self) -> None:
        """Scenario: Brand keywords are dropped from a candidate."""
        service, _ = _service(_answer({**_DARK, "keywords": [3, "night"]}))
        [candidate] = await service.generate(_REQUEST)
        assert candidate.keywords == ("night",)


class TestUnavailable:
    @pytest.mark.parametrize(
        "answer",
        [
            RuntimeError("provider down"),
            TimeoutError(),
            "sorry, I cannot help",
            json.dumps({"candidates": []}),
            json.dumps({"palettes": [_DARK]}),
            json.dumps({"candidates": [{**_DARK, "primary": "nope"}]}),
        ],
    )
    @pytest.mark.asyncio
    async def test_no_usable_answer_raises(self, answer: str | Exception) -> None:
        """Scenario: The generator is unavailable when the LLM fails."""
        service, _ = _service(answer)
        with pytest.raises(PaletteGenerationError):
            await service.generate(_REQUEST)
