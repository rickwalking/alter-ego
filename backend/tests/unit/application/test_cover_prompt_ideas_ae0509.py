"""The cover-photo prompt ideas service ("Mais ideias").

Feature: Prompt ideas for a new cover photo
(tests/features/cover_prompt_ideas_ae0509.feature). The LLM is a scripted fake.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager

import pytest

import rag_backend.application.services.carousel.cover_prompt_ideas_service as svc
from rag_backend.application.services.carousel.cover_prompt_ideas_service import (
    CoverIdeasPalette,
    CoverIdeasPorts,
    CoverIdeasRequest,
    CoverPromptIdeasError,
    CoverPromptIdeasService,
    parse_ideas,
)
from rag_backend.domain.constants.cover_prompt_ideas import (
    IDEA_MAX_LEN,
    NO_PALETTE_HINT,
    IdeaLocale,
)
from rag_backend.domain.constants.palette_types import PaletteMode

_PALETTE = CoverIdeasPalette(
    name="Noite Azul",
    mode=PaletteMode.DARK,
    background="#0b1020",
    primary="#38bdf8",
    accent="#fde68a",
)
_IDEAS = [f"Retrato de meio corpo número {n}, fundo azul-noite" for n in range(8)]


class _ScriptedLLM:
    """Answers its script in order (an Exception is raised); counts calls."""

    def __init__(self, *answers: str | BaseException) -> None:
        self._answers = list(answers)
        self.calls = 0

    async def complete(self, prompt: str) -> str:
        answer = self._answers[min(self.calls, len(self._answers) - 1)]
        self.calls += 1
        if isinstance(answer, BaseException):
            raise answer
        return answer


class _Recorder:
    """Records what the prompt renderer and the trace received."""

    def __init__(self) -> None:
        self.prompts: list[tuple[str, str, IdeaLocale]] = []
        self.traced: list[str] = []

    def render(self, topic: str, palette: str, locale: IdeaLocale) -> str:
        self.prompts.append((topic, palette, locale))
        return f"{topic}|{palette}|{locale}"

    def trace(self, user_id: str) -> AbstractContextManager[object]:
        self.traced.append(user_id)
        return _scope()


@contextmanager
def _scope() -> Iterator[object]:
    yield object()


def _service(llm: _ScriptedLLM, recorder: _Recorder) -> CoverPromptIdeasService:
    return CoverPromptIdeasService(
        CoverIdeasPorts(llm=llm, render_prompt=recorder.render, trace=recorder.trace)
    )


def _request(
    palette: CoverIdeasPalette | None = _PALETTE,
    locale: IdeaLocale = IdeaLocale.PT,
) -> CoverIdeasRequest:
    return CoverIdeasRequest(
        topic="IA no trabalho", palette=palette, locale=locale, user_id="u-1"
    )


def _answer(ideas: list[object]) -> str:
    return json.dumps({"ideas": ideas})


class TestSuggest:
    @pytest.mark.asyncio
    async def test_topic_and_palette_give_six_ideas(self) -> None:
        """Scenario: The topic and palette give three to six ideas."""
        llm, recorder = _ScriptedLLM(_answer(_IDEAS[:6])), _Recorder()

        ideas = await _service(llm, recorder).suggest(_request())

        assert ideas == _IDEAS[:6]
        assert recorder.prompts == [
            (
                "IA no trabalho",
                "Noite Azul: dark background #0b1020, primary #38bdf8, accent #fde68a",
                IdeaLocale.PT,
            )
        ]
        assert recorder.traced == ["u-1"]
        assert llm.calls == 1

    @pytest.mark.asyncio
    async def test_no_palette_says_so(self) -> None:
        """Scenario: Without a palette the model picks colours for the topic."""
        llm, recorder = _ScriptedLLM(_answer(_IDEAS[:4])), _Recorder()

        ideas = await _service(llm, recorder).suggest(_request(palette=None))

        assert ideas == _IDEAS[:4]
        assert recorder.prompts[0][1] == NO_PALETTE_HINT

    @pytest.mark.asyncio
    async def test_locale_reaches_the_prompt(self) -> None:
        """Scenario: The ideas come in the dashboard's language."""
        llm, recorder = _ScriptedLLM(_answer(_IDEAS[:4])), _Recorder()

        await _service(llm, recorder).suggest(_request(locale=IdeaLocale.EN))

        assert recorder.prompts[0][2] == IdeaLocale.EN

    @pytest.mark.asyncio
    async def test_a_short_answer_is_asked_once_more(self) -> None:
        """Scenario: A short answer is asked once more."""
        first = _answer(_IDEAS[:2])
        second = _answer([_IDEAS[1].upper(), *_IDEAS[2:5]])
        llm, recorder = _ScriptedLLM(first, second), _Recorder()

        ideas = await _service(llm, recorder).suggest(_request())

        assert ideas == _IDEAS[:5]
        assert llm.calls == 2
        assert len(recorder.prompts) == 1

    @pytest.mark.asyncio
    async def test_a_failing_first_call_is_retried(self) -> None:
        """Scenario: A short answer is asked once more."""
        llm = _ScriptedLLM(RuntimeError("down"), _answer(_IDEAS[:3]))

        ideas = await _service(llm, _Recorder()).suggest(_request())

        assert ideas == _IDEAS[:3]
        assert llm.calls == 2


class TestUnavailable:
    @pytest.mark.parametrize(
        "answers",
        [
            (RuntimeError("down"),),
            ("not json",),
            (_answer(_IDEAS[:2]),),
            ("",),
            (json.dumps({"other": _IDEAS}),),
        ],
    )
    @pytest.mark.asyncio
    async def test_unavailable_after_two_tries(
        self, answers: tuple[str | BaseException, ...]
    ) -> None:
        """Scenario: The ideas are unavailable when the LLM fails."""
        llm = _ScriptedLLM(*answers)

        with pytest.raises(CoverPromptIdeasError) as caught:
            await _service(llm, _Recorder()).suggest(_request())

        assert caught.value.code == "cover_prompt_ideas_unavailable"
        assert llm.calls == 2

    @pytest.mark.asyncio
    async def test_a_timeout_counts_as_no_ideas(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: The ideas are unavailable when the LLM fails."""
        monkeypatch.setattr(svc, "IDEAS_TIMEOUT_SECONDS", 0.01)

        class _Slow:
            calls = 0

            async def complete(self, prompt: str) -> str:
                self.calls += 1
                await asyncio.sleep(1)
                return _answer(_IDEAS)

        slow = _Slow()
        service = CoverPromptIdeasService(
            CoverIdeasPorts(
                llm=slow, render_prompt=_Recorder().render, trace=_Recorder().trace
            )
        )

        with pytest.raises(CoverPromptIdeasError):
            await service.suggest(_request())
        assert slow.calls == 2


class TestParseIdeas:
    def test_unusable_ideas_are_dropped(self) -> None:
        """Scenario: Unusable ideas are dropped."""
        raw: list[object] = [
            "curto",
            "x" * (IDEA_MAX_LEN + 1),
            "Retrato com <script>alert</script> ao fundo",
            "Retrato com {{ topic }} ao fundo e luz",
            42,
            None,
            "  Retrato   lateral,\n fundo   liso  ",
            "retrato lateral, fundo liso",
            *_IDEAS,
        ]

        ideas = parse_ideas(_answer(raw))

        assert ideas == ["Retrato lateral, fundo liso", *_IDEAS[:5]]

    def test_an_idea_at_the_limits_is_kept(self) -> None:
        """Scenario: Unusable ideas are dropped."""
        shortest, longest = "x" * 12, "y" * IDEA_MAX_LEN
        assert parse_ideas(_answer([shortest, longest, "z" * 11])) == [
            shortest,
            longest,
        ]

    def test_a_bare_list_and_a_fenced_answer_are_read(self) -> None:
        """Scenario: The topic and palette give three to six ideas."""
        fenced = f"```json\n{json.dumps(_IDEAS[:3])}\n```"
        assert parse_ideas(fenced) == _IDEAS[:3]

    @pytest.mark.parametrize("answer", ["nope", "[", '"just text"', "{}"])
    def test_unreadable_answers_have_no_ideas(self, answer: str) -> None:
        """Scenario: The ideas are unavailable when the LLM fails."""
        assert parse_ideas(answer) == []
