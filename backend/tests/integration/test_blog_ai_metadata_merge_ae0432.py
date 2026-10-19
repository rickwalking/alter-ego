"""AI suggest/improve merge onto the latest metadata (AE-0432).

Feature: backend/tests/features/blog_ai_metadata_merge_ae0432.feature
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.application.services.blog_post_ai_service import BlogPostAIService
from tests.blog_v2_support import v2_content
from tests.integration.blog_editor_support_ae0424 import (
    BLOG_POSTS_URL,
    EditorClients,
    create_post,
    editor_clients,
    get_post,
    set_fields,
)

GENERATIONS_KEY = "blog_image_generations"
EXTERNAL_ACTION = {"action": "ai_generate_image"}


@pytest.fixture
async def clients(tmp_path: Path) -> AsyncIterator[EditorClients]:
    async with editor_clients(tmp_path) as built:
        yield built


async def _reserve_one(post_id: str) -> None:
    """Commit an image budget reservation from another session."""
    from rag_backend.api.dependencies.blog_image_budget import (
        BudgetReservation,
        reserve_image_budget,
    )
    from rag_backend.infrastructure.database.config import get_session_maker

    async with get_session_maker()() as session:
        await reserve_image_budget(session, BudgetReservation(post_id=post_id, cap=30))


def _service_running(
    monkeypatch: pytest.MonkeyPatch,
    during: Callable[[], Awaitable[None]],
    answer: str,
) -> MagicMock:
    """A real AI service whose LLM call runs ``during()`` before answering."""
    from rag_backend.api.routes import blog_post_ai

    async def generate(*_args: object, **_kwargs: object) -> str:
        await during()
        return answer

    llm = MagicMock()
    llm.generate = AsyncMock(side_effect=generate)
    service = BlogPostAIService(llm_service=llm)
    monkeypatch.setattr(blog_post_ai, "_build_ai_service", lambda: service)
    return llm


async def _seed(clients: EditorClients) -> dict:
    post = await create_post(clients.author, v2_content("Corpo"))
    await set_fields(
        post["id"],
        ai_generation_metadata={GENERATIONS_KEY: 1, "ai_actions": [EXTERNAL_ACTION]},
    )
    return post


class TestReservationDuringTheCall:
    # Scenario: An image budget reservation committed during ai-suggest is kept
    async def test_suggest_keeps_a_concurrent_reservation(
        self, clients: EditorClients, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        post = await _seed(clients)
        llm = _service_running(
            monkeypatch,
            lambda: _reserve_one(post["id"]),
            '{"suggested_text": "Melhor", "explanation": "e"}',
        )
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/ai-suggest", json={"text": "Corpo"}
        )
        assert response.status_code == 200, response.text
        llm.generate.assert_awaited_once()
        metadata = (await get_post(clients.author, post["id"]))[
            "ai_generation_metadata"
        ]
        assert metadata[GENERATIONS_KEY] == 2
        actions = [entry["action"] for entry in metadata["ai_actions"]]
        assert actions == ["ai_generate_image", "ai_suggest"]

    # Scenario: An image budget reservation committed during ai-improve is kept
    async def test_improve_keeps_a_concurrent_reservation(
        self, clients: EditorClients, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        post = await _seed(clients)
        _service_running(monkeypatch, lambda: _reserve_one(post["id"]), "Melhorado")
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/ai-improve", json={"text": "Corpo"}
        )
        assert response.status_code == 200, response.text
        metadata = (await get_post(clients.author, post["id"]))[
            "ai_generation_metadata"
        ]
        assert metadata[GENERATIONS_KEY] == 2
        assert metadata["ai_actions"][-1]["action"] == "ai_improve"
        assert metadata["ai_action_count"] == len(metadata["ai_actions"])


class TestSuggestionsMerge:
    # Scenario: A suggestion stored meanwhile is not lost
    async def test_concurrent_suggestion_is_kept(
        self, clients: EditorClients, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        post = await _seed(clients)
        earlier = {"suggested_text": "Outra", "applied": False}

        async def store_other() -> None:
            await set_fields(post["id"], ai_suggestions=[earlier])

        _service_running(monkeypatch, store_other, '{"suggested_text": "Nova"}')
        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/ai-suggest", json={"text": "Corpo"}
        )
        assert response.status_code == 200, response.text
        stored = (await get_post(clients.author, post["id"]))["ai_suggestions"]
        assert [s["suggested_text"] for s in stored] == ["Outra", "Nova"]


class TestReservationLocksPerPost:
    # Scenario: Reservations on different posts do not wait on each other
    async def test_another_posts_reservation_is_not_blocked(
        self, clients: EditorClients
    ) -> None:
        from rag_backend.api.dependencies.blog_image_budget import _reservation_lock

        first = await create_post(clients.author, v2_content("A"))
        second = (
            await clients.author.post(
                BLOG_POSTS_URL, json={"title": "Outro post", "content": v2_content("B")}
            )
        ).json()
        assert _reservation_lock(first["id"]) is _reservation_lock(first["id"])
        assert _reservation_lock(first["id"]) is not _reservation_lock(second["id"])
        async with _reservation_lock(first["id"]):
            await asyncio.wait_for(_reserve_one(second["id"]), timeout=5)
        stored = (await get_post(clients.author, second["id"]))[
            "ai_generation_metadata"
        ]
        assert stored[GENERATIONS_KEY] == 1
