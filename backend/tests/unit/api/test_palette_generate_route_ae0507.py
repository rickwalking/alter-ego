"""Route-level tests of ``POST /api/palettes/generate``.

Feature: Generate palette candidates from a description
(tests/features/palette_generate_ae0507.feature). The real app over an
in-memory DB, with the generator's LLM replaced by a canned answer.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Iterator
from contextlib import AbstractContextManager, contextmanager

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

import rag_backend.infrastructure.database.config as db_config
from rag_backend.api.dependencies import require_authenticated_user
from rag_backend.api.dependencies.palette_generation import (
    get_palette_generation_service,
)
from rag_backend.api.middleware.rate_limiting import limiter, user_or_address_key
from rag_backend.application.services.carousel.palette_generation_service import (
    PaletteGenerationPorts,
    PaletteGenerationService,
)
from rag_backend.bootstrap.app_factory import create_app
from rag_backend.domain.models import User
from rag_backend.domain.models.user import UserRole
from rag_backend.infrastructure.config.settings import get_settings
from rag_backend.infrastructure.database.config import Base

_USER = User(
    email="owner@test.dev",
    full_name="Owner",
    hashed_password="x",
    role=UserRole.EDITOR,
)
_CANDIDATES = [
    {
        "name": "Noite Azul",
        "primary": "#38bdf8",
        "accent": "#1e2a44",
        "background": "#0b1020",
        "mode": "dark",
        "keywords": ["night"],
    },
    {
        "name": "Areia",
        "primary": "#1d4ed8",
        "accent": "#9a3412",
        "background": "#f8f5ee",
        "mode": "dark",
        "keywords": ["sand", "openai"],
    },
    {
        "name": "Floresta",
        "primary": "#86efac",
        "accent": "#fde68a",
        "background": "#052e16",
        "mode": "dark",
        "keywords": [],
    },
]


class _CannedLLM:
    """Answers a fixed text, or raises it; counts its calls."""

    def __init__(self, answer: str | Exception) -> None:
        self.answer = answer
        self.calls = 0

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        self.calls += 1
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


@contextmanager
def _no_trace() -> Iterator[object]:
    yield object()


def _trace(_user_id: str) -> AbstractContextManager[object]:
    return _no_trace()


def _env() -> None:
    get_settings.cache_clear()
    os.environ["FEATURE_FLAG_PALETTE_CATALOG"] = "true"
    os.environ["SECRET_KEY"] = "test-secret-for-palette-generate-aa!"
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-palette-generate!"


@pytest_asyncio.fixture
async def app() -> AsyncIterator[FastAPI]:
    """The app over an in-memory DB with the palette flag on."""
    _env()
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


def _use_llm(app: FastAPI, llm: _CannedLLM) -> None:
    ports = PaletteGenerationPorts(llm=llm, render_prompt=lambda d: d, trace=_trace)
    app.dependency_overrides[get_palette_generation_service] = lambda: (
        PaletteGenerationService(ports)
    )
    app.dependency_overrides[require_authenticated_user] = lambda: _USER


async def _post(app: FastAPI, body: dict[str, str]) -> tuple[int, dict[str, object]]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/palettes/generate", json=body)
        listing = await client.get("/api/palettes")
    if listing.status_code == 200:
        assert listing.json()["custom"] == []
    return response.status_code, response.json()


class TestGenerate:
    @pytest.mark.asyncio
    async def test_three_candidates_and_nothing_saved(self, app: FastAPI) -> None:
        """Scenario: A description returns three validated candidates."""
        _use_llm(app, _CannedLLM(json.dumps({"candidates": _CANDIDATES})))
        status, body = await _post(app, {"description": "  noite azul  "})
        assert status == 200
        candidates = body["candidates"]
        assert isinstance(candidates, list)
        assert [c["name"] for c in candidates] == ["Noite Azul", "Areia", "Floresta"]
        assert set(candidates[0]) == {
            "name",
            "primary",
            "accent",
            "background",
            "mode",
            "keywords",
            "contrast",
        }

    @pytest.mark.asyncio
    async def test_contrast_is_repaired(self, app: FastAPI) -> None:
        """Scenario: A low-contrast colour is repaired before it is returned."""
        _use_llm(app, _CannedLLM(json.dumps({"candidates": _CANDIDATES})))
        _, body = await _post(app, {"description": "noite azul"})
        candidates = body["candidates"]
        assert isinstance(candidates, list)
        first = candidates[0]
        assert first["accent"] != "#1e2a44"
        assert min(first["contrast"].values()) >= 4.5

    @pytest.mark.asyncio
    async def test_mode_and_keywords_are_sanitised(self, app: FastAPI) -> None:
        """Scenarios covered.

        Scenario: The mode follows the background.
        Scenario: Brand keywords are dropped from a candidate.
        """
        _use_llm(app, _CannedLLM(json.dumps({"candidates": _CANDIDATES})))
        _, body = await _post(app, {"description": "areia clara"})
        candidates = body["candidates"]
        assert isinstance(candidates, list)
        assert candidates[1]["mode"] == "light"
        assert candidates[1]["keywords"] == ["sand"]


class TestFailures:
    @pytest.mark.parametrize("answer", [RuntimeError("down"), "not json at all"])
    @pytest.mark.asyncio
    async def test_llm_failure_is_503(
        self, app: FastAPI, answer: str | Exception
    ) -> None:
        """Scenario: The generator is unavailable when the LLM fails."""
        _use_llm(app, _CannedLLM(answer))
        status, body = await _post(app, {"description": "noite azul"})
        assert status == 503
        assert body["detail"] == "palette_generation_unavailable"

    @pytest.mark.parametrize("description", ["ab", "  ab   "])
    @pytest.mark.asyncio
    async def test_short_description_is_422(
        self, app: FastAPI, description: str
    ) -> None:
        """Scenario: A too short description is rejected."""
        llm = _CannedLLM(json.dumps({"candidates": _CANDIDATES}))
        _use_llm(app, llm)
        status, _ = await _post(app, {"description": description})
        assert status == 422
        assert llm.calls == 0

    @pytest.mark.asyncio
    async def test_anonymous_is_401(self, app: FastAPI) -> None:
        """Scenario: The generator needs a logged-in user."""
        llm = _CannedLLM(json.dumps({"candidates": _CANDIDATES}))
        _use_llm(app, llm)
        del app.dependency_overrides[require_authenticated_user]
        status, _ = await _post(app, {"description": "noite azul"})
        assert status == 401
        assert llm.calls == 0


class TestRateLimit:
    @pytest.mark.asyncio
    async def test_sixth_generation_in_a_minute_is_429(self, app: FastAPI) -> None:
        """Scenario: The generator is rate limited."""
        llm = _CannedLLM(json.dumps({"candidates": _CANDIDATES}))
        _use_llm(app, llm)
        statuses = [
            (await _post(app, {"description": "noite azul"}))[0] for _ in range(6)
        ]
        assert statuses == [200, 200, 200, 200, 200, 429]
        assert llm.calls == 5

    @pytest.mark.asyncio
    async def test_each_user_has_their_own_limit(self, app: FastAPI) -> None:
        """Scenario: The generator is rate limited per user."""
        llm = _CannedLLM(json.dumps({"candidates": _CANDIDATES}))
        _use_llm(app, llm)
        for _ in range(5):
            await _post(app, {"description": "noite azul"})
        other = User(
            email="other@test.dev",
            full_name="Other",
            hashed_password="x",
            role=UserRole.EDITOR,
        )
        app.dependency_overrides[require_authenticated_user] = lambda: other

        status, _ = await _post(app, {"description": "noite azul"})

        assert status == 200
        assert llm.calls == 6


class TestRateLimitKey:
    def test_the_recorded_user_is_the_key(self) -> None:
        """Scenario: The generator is rate limited per user."""
        request = Request({"type": "http", "client": ("10.0.0.1", 1), "headers": []})
        assert user_or_address_key(request) == "10.0.0.1"
        request.state.rate_limit_user_id = "u-1"
        assert user_or_address_key(request) == "user:u-1"
