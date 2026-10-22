"""Knowledge 500s: fixed client message, exception in the server log.

Gherkin: tests/features/knowledge_error_detail_ae0452.feature
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest
import structlog

from rag_backend.api.constants import (
    ERR_DOCUMENT_PROCESSING_FAILED,
    ERR_SEARCH_FAILED,
)
from rag_backend.api.dependencies.knowledge import get_knowledge_service
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


def _logged_with_exception(logs: list[dict[str, object]], event: str) -> bool:
    return any(entry.get("event") == event and entry.get("exc_info") for entry in logs)


@pytest.mark.integration
class TestKnowledgeErrorDetail:
    async def test_failed_search_is_fixed_500_and_logged(
        self, kb_env: KnowledgeEnv, failing_service: AsyncMock
    ) -> None:
        # Scenario: A failed search answers a fixed 500 and logs the error
        with structlog.testing.capture_logs() as logs:
            async with kb_env.client_for(kb_env.owner) as client:
                response = await client.post(
                    "/api/search", json={"query": "artificial intelligence"}
                )

        assert response.status_code == 500
        assert response.json()["detail"] == ERR_SEARCH_FAILED
        assert "sk-live" not in response.text
        assert _logged_with_exception(logs, "knowledge_search_failed")
        assert failing_service.search.await_count == 1

    async def test_failed_ingest_is_fixed_500_and_logged(
        self, kb_env: KnowledgeEnv, failing_service: AsyncMock
    ) -> None:
        # Scenario: A failed document ingest answers a fixed 500 and logs the error
        with structlog.testing.capture_logs() as logs:
            async with kb_env.client_for(kb_env.owner) as client:
                response = await client.post(
                    "/api/documents/upload",
                    files={"file": ("notes.txt", b"Some notes", "text/plain")},
                )

        assert response.status_code == 500
        assert response.json()["detail"] == ERR_DOCUMENT_PROCESSING_FAILED
        assert "sk-live" not in response.text
        assert _logged_with_exception(logs, "knowledge_ingest_failed")
        assert failing_service.ingest.await_count == 1
