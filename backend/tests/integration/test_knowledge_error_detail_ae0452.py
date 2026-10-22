"""Knowledge 500s: fixed client message, exception in the server log.

Gherkin: tests/features/knowledge_error_detail_ae0452.feature
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from rag_backend.api.constants import (
    ERR_DOCUMENT_PROCESSING_FAILED,
    ERR_SEARCH_FAILED,
)
from rag_backend.api.dependencies.knowledge import get_knowledge_service
from rag_backend.api.routes import documents as documents_route
from rag_backend.api.routes import search as search_route
from rag_backend.application.services.document_pipeline import (
    PIPELINE_FAILURE_LOGGED,
)
from tests.integration.test_knowledge_safety_net import (
    KnowledgeEnv,
    kb_env,
)

SECRET = "pinecone https://idx-1234.svc.internal api_key=sk-live-123"

__all__ = ["kb_env"]


@pytest.fixture
def failing_service(kb_env: KnowledgeEnv) -> Iterator[AsyncMock]:
    service = AsyncMock()
    service.search = AsyncMock(side_effect=RuntimeError(SECRET))
    service.ingest = AsyncMock(side_effect=RuntimeError(SECRET))
    app = kb_env.app
    app.dependency_overrides[get_knowledge_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_knowledge_service, None)


@pytest.fixture
def route_loggers(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    loggers = {"search": MagicMock(), "documents": MagicMock()}
    monkeypatch.setattr(search_route, "logger", loggers["search"])
    monkeypatch.setattr(documents_route, "logger", loggers["documents"])
    return loggers


@pytest.mark.integration
class TestKnowledgeErrorDetail:
    async def test_failed_search_is_fixed_500_and_logged(
        self,
        kb_env: KnowledgeEnv,
        failing_service: AsyncMock,
        route_loggers: dict[str, MagicMock],
    ) -> None:
        # Scenario: A failed search answers a fixed 500 and logs the error
        # Scenario: Failure logs carry safe context only
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.post(
                "/api/search", json={"query": "artificial intelligence"}
            )

        assert response.status_code == 500
        assert response.json()["detail"] == ERR_SEARCH_FAILED
        assert "sk-live" not in response.text
        route_loggers["search"].exception.assert_called_once_with(
            "knowledge_search_failed",
            user_id=str(kb_env.owner.id),
            top_k=5,
            query_length=len("artificial intelligence"),
        )
        assert failing_service.search.await_count == 1

    async def test_failed_ingest_is_fixed_500_and_logged(
        self,
        kb_env: KnowledgeEnv,
        failing_service: AsyncMock,
        route_loggers: dict[str, MagicMock],
    ) -> None:
        # Scenario: A failed document ingest answers a fixed 500 and logs the error
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.post(
                "/api/documents/upload",
                files={"file": ("notes.txt", b"Some notes", "text/plain")},
            )

        assert response.status_code == 500
        assert response.json()["detail"] == ERR_DOCUMENT_PROCESSING_FAILED
        assert "sk-live" not in response.text
        route_loggers["documents"].exception.assert_called_once_with(
            "knowledge_ingest_failed",
            user_id=str(kb_env.owner.id),
            scope="personal",
            content_type="text/plain",
            content_length=len("Some notes"),
            error_type="RuntimeError",
        )
        assert failing_service.ingest.await_count == 1

    async def test_pipeline_logged_ingest_failure_logs_no_second_traceback(
        self,
        kb_env: KnowledgeEnv,
        failing_service: AsyncMock,
        route_loggers: dict[str, MagicMock],
    ) -> None:
        # Scenario: A pipeline failure is logged with its traceback once
        logged = RuntimeError(SECRET)
        logged.add_note(PIPELINE_FAILURE_LOGGED)
        failing_service.ingest = AsyncMock(side_effect=logged)
        async with kb_env.client_for(kb_env.owner) as client:
            response = await client.post(
                "/api/documents/upload",
                files={"file": ("notes.txt", b"Some notes", "text/plain")},
            )

        assert response.status_code == 500
        route_loggers["documents"].exception.assert_not_called()
        route_loggers["documents"].error.assert_called_once()
        assert route_loggers["documents"].error.call_args.args == (
            "knowledge_ingest_failed",
        )
