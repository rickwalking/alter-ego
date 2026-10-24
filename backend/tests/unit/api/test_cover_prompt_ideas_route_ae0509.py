"""Route-level tests of ``POST /api/carousels/cover-prompt-ideas``.

Feature: Prompt ideas for a new cover photo
(tests/features/cover_prompt_ideas_ae0509.feature). The real app over an
in-memory DB, with the ideas' LLM replaced by a canned answer.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Iterator
from contextlib import AbstractContextManager, contextmanager

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import rag_backend.api.dependencies.cover_prompt_ideas as composition
import rag_backend.infrastructure.database.config as db_config
from rag_backend.api.dependencies import require_authenticated_user
from rag_backend.api.dependencies.cover_prompt_ideas import (
    get_cover_prompt_ideas_service,
)
from rag_backend.api.middleware.rate_limiting import limiter
from rag_backend.application.services.carousel.cover_prompt_ideas_service import (
    CoverIdeasPorts,
    CoverIdeasRequest,
    CoverPromptIdeasService,
)
from rag_backend.bootstrap.app_factory import create_app
from rag_backend.domain.constants.cover_prompt_ideas import IdeaLocale
from rag_backend.domain.models import User
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.config import Base
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from tests.unit.llm_fakes_ae0391 import CallLog, FakeChat

_URL = "/api/carousels/cover-prompt-ideas"
_USER = User(
    email="owner@test.dev",
    full_name="Owner",
    hashed_password="x",
    role=UserRole.EDITOR,
)
_IDEAS = [f"Retrato de três quartos número {n}, fundo azul-noite" for n in range(6)]
_PALETTE = {
    "name": "Noite Azul",
    "mode": "dark",
    "background": "#0B1020",
    "primary": "#38bdf8",
    "accent": "#fde68a",
}


class _CannedLLM:
    """Answers a fixed text, or raises it; counts its calls."""

    def __init__(self, answer: str | Exception) -> None:
        self.answer = answer
        self.calls = 0

    async def complete(self, prompt: str) -> str:
        self.calls += 1
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


class _Prompts:
    """The prompt renderer: records the topic, palette line and locale it got."""

    def __init__(self) -> None:
        self.seen: list[tuple[str, str, IdeaLocale]] = []

    def __call__(self, topic: str, palette: str, locale: IdeaLocale) -> str:
        self.seen.append((topic, palette, locale))
        return topic


@contextmanager
def _no_trace() -> Iterator[object]:
    yield object()


def _trace(_user_id: str) -> AbstractContextManager[object]:
    return _no_trace()


@pytest_asyncio.fixture
async def app() -> AsyncIterator[FastAPI]:
    """The app over an in-memory DB."""
    get_settings.cache_clear()
    os.environ["SECRET_KEY"] = "test-secret-for-cover-prompt-ideas!"
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-cover-prompt-ideas"
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    limiter.reset()
    application = create_app()
    yield application
    application.dependency_overrides.clear()
    await engine.dispose()
    get_settings.cache_clear()


def _use_llm(app: FastAPI, llm: _CannedLLM) -> _Prompts:
    prompts = _Prompts()
    ports = CoverIdeasPorts(llm=llm, render_prompt=prompts, trace=_trace)
    app.dependency_overrides[get_cover_prompt_ideas_service] = lambda: (
        CoverPromptIdeasService(ports)
    )
    app.dependency_overrides[require_authenticated_user] = lambda: _USER
    return prompts


async def _post(app: FastAPI, body: dict[str, object]) -> tuple[int, dict[str, object]]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(_URL, json=body)
    return response.status_code, response.json()


async def _carousel_count() -> int:
    sessions = async_sessionmaker(db_config.c_engine)
    async with sessions() as session:
        result = await session.execute(
            select(func.count()).select_from(CarouselProjectModel)
        )
    return int(result.scalar_one())


class TestIdeas:
    @pytest.mark.asyncio
    async def test_topic_and_palette_give_six_ideas(self, app: FastAPI) -> None:
        """Scenario: The topic and palette give three to six ideas."""
        prompts = _use_llm(app, _CannedLLM(json.dumps({"ideas": _IDEAS})))

        status, body = await _post(
            app, {"topic": "  IA no trabalho  ", "palette": _PALETTE}
        )

        assert status == 200
        assert body == {"ideas": _IDEAS}
        assert prompts.seen == [
            (
                "IA no trabalho",
                "Noite Azul: dark background #0b1020, primary #38bdf8, accent #fde68a",
                IdeaLocale.PT,
            )
        ]
        assert await _carousel_count() == 0

    @pytest.mark.asyncio
    async def test_no_palette_and_english(self, app: FastAPI) -> None:
        """Scenarios covered.

        Scenario: Without a palette the model picks colours for the topic.
        Scenario: The ideas come in the dashboard's language.
        """
        prompts = _use_llm(app, _CannedLLM(json.dumps({"ideas": _IDEAS[:4]})))

        status, body = await _post(
            app, {"topic": "AI at work", "palette": None, "locale": "en"}
        )

        assert status == 200
        assert body == {"ideas": _IDEAS[:4]}
        assert prompts.seen[0][2] == IdeaLocale.EN
        assert "no fixed palette" in prompts.seen[0][1]


class TestFailures:
    @pytest.mark.parametrize(
        "answer", [RuntimeError("down"), "not json", json.dumps({"ideas": _IDEAS[:2]})]
    )
    @pytest.mark.asyncio
    async def test_unavailable_is_503(
        self, app: FastAPI, answer: str | Exception
    ) -> None:
        """Scenario: The ideas are unavailable when the LLM fails."""
        llm = _CannedLLM(answer)
        _use_llm(app, llm)

        status, body = await _post(app, {"topic": "IA no trabalho"})

        assert status == 503
        assert body["detail"] == "cover_prompt_ideas_unavailable"
        assert llm.calls == 2

    @pytest.mark.parametrize(
        "body",
        [
            {"topic": "IA no trabalho", "thesis": "minha tese pessoal"},
            {"topic": "IA no trabalho", "palette": {**_PALETTE, "accent": "blue"}},
            {"topic": "IA no trabalho", "palette": {**_PALETTE, "name": "<b>x</b>"}},
            {"topic": "IA no trabalho", "palette": {**_PALETTE, "photo": "x"}},
            {"topic": "IA no trabalho", "locale": "fr"},
            {"topic": "ab"},
            {"topic": "   ab    "},
            {"topic": "x" * 501},
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_input_is_422(
        self, app: FastAPI, body: dict[str, object]
    ) -> None:
        """Scenarios covered.

        Scenario: Only the topic and the palette are accepted.
        Scenario: A too short topic is rejected.
        """
        llm = _CannedLLM(json.dumps({"ideas": _IDEAS}))
        _use_llm(app, llm)

        status, _ = await _post(app, body)

        assert status == 422
        assert llm.calls == 0

    @pytest.mark.asyncio
    async def test_anonymous_is_401(self, app: FastAPI) -> None:
        """Scenario: The ideas need a logged-in editor."""
        llm = _CannedLLM(json.dumps({"ideas": _IDEAS}))
        _use_llm(app, llm)
        del app.dependency_overrides[require_authenticated_user]

        status, _ = await _post(app, {"topic": "IA no trabalho"})

        assert status == 401
        assert llm.calls == 0


class TestRateLimit:
    @pytest.mark.asyncio
    async def test_eleventh_call_is_429_but_not_for_another_user(
        self, app: FastAPI
    ) -> None:
        """Scenario: The ideas are rate limited per user."""
        llm = _CannedLLM(json.dumps({"ideas": _IDEAS}))
        _use_llm(app, llm)
        body: dict[str, object] = {"topic": "IA no trabalho"}

        statuses = [(await _post(app, body))[0] for _ in range(11)]
        other = User(
            email="other@test.dev",
            full_name="Other",
            hashed_password="x",
            role=UserRole.EDITOR,
        )
        app.dependency_overrides[require_authenticated_user] = lambda: other
        other_status, _ = await _post(app, body)

        assert statuses == [200] * 10 + [429]
        assert other_status == 200
        assert llm.calls == 11


class TestComposition:
    @pytest.mark.asyncio
    async def test_the_service_runs_on_the_fast_queue(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: The model call carries the token cap and temperature."""
        log = CallLog()
        fast = FakeChat(reply=lambda _prompt: json.dumps({"ideas": _IDEAS}), log=log)

        class _Fast:
            chat_model = fast

        class _Container:
            def fast_llm_service(self) -> _Fast:
                return _Fast()

        monkeypatch.setattr(composition, "get_container", _Container)

        ideas = await get_cover_prompt_ideas_service().suggest(
            CoverIdeasRequest(
                topic="IA no trabalho",
                palette=None,
                locale=IdeaLocale.PT,
                user_id="u-1",
            )
        )

        assert ideas == _IDEAS
        assert len(log.kwargs) == 1
