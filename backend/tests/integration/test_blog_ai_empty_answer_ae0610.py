"""An empty model answer on blog suggest and improve is a typed 503.

Feature: backend/tests/features/llm_service_params_ae0610.feature
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.application.services.blog_post_ai_service import BlogPostAIService
from rag_backend.infrastructure.external.routed_chat_model import EmptyLLMResponseError
from tests.blog_v2_support import v2_content
from tests.integration.blog_editor_support_ae0424 import (
    BLOG_POSTS_URL,
    EditorClients,
    create_post,
    editor_clients,
    get_post,
)

_MODEL_ID = "secret-model-id"
_SAFE_MESSAGE = "The model returned nothing. Please try again."


@pytest.fixture
async def clients(tmp_path: Path) -> AsyncIterator[EditorClients]:
    async with editor_clients(tmp_path) as built:
        yield built


def _service_failing_with(monkeypatch: pytest.MonkeyPatch, failure: Exception) -> None:
    """The real AI service over an LLM that raises ``failure``."""
    from rag_backend.api.routes import blog_post_ai

    llm = MagicMock()
    llm.generate = AsyncMock(side_effect=failure)
    service = BlogPostAIService(llm_service=llm)
    monkeypatch.setattr(blog_post_ai, "_build_ai_service", lambda: service)


@pytest.fixture
def empty_model(monkeypatch: pytest.MonkeyPatch) -> None:
    _service_failing_with(monkeypatch, EmptyLLMResponseError(_MODEL_ID))


@pytest.mark.usefixtures("empty_model")
class TestEmptyAnswer:
    # Scenario: An empty answer on a blog AI route is a typed 503
    @pytest.mark.parametrize("route", ["ai-suggest", "ai-improve"])
    async def test_the_route_answers_a_typed_503(
        self, clients: EditorClients, route: str
    ) -> None:
        post = await create_post(clients.author, v2_content("Corpo"))

        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/{route}", json={"text": "Corpo"}
        )

        assert response.status_code == 503, response.text
        assert response.json() == {
            "detail": _SAFE_MESSAGE,
            "code": "provider_unavailable",
        }
        assert _MODEL_ID not in response.text
        stored = await get_post(clients.author, post["id"])
        assert not stored["ai_generation_metadata"].get("ai_actions")

    # Scenario: An empty answer on ai-suggest stores no suggestion
    async def test_suggest_stores_nothing(self, clients: EditorClients) -> None:
        post = await create_post(clients.author, v2_content("Corpo"))

        response = await clients.author.post(
            f"{BLOG_POSTS_URL}/{post['id']}/ai-suggest", json={"text": "Corpo"}
        )

        assert response.status_code == 503, response.text
        stored = await get_post(clients.author, post["id"])
        assert stored["ai_suggestions"] == []


# Scenario: A bad request on a blog AI route stays a 400
@pytest.mark.parametrize("route", ["ai-suggest", "ai-improve"])
async def test_a_bad_request_stays_a_400(
    clients: EditorClients, monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    _service_failing_with(monkeypatch, ValueError("bad input"))
    post = await create_post(clients.author, v2_content("Corpo"))

    response = await clients.author.post(
        f"{BLOG_POSTS_URL}/{post['id']}/{route}", json={"text": "Corpo"}
    )

    assert response.status_code == 400, response.text
