"""Knowledge safety-net integration tests (AE-0088).

Behavioral safety net for the Phase 2 Knowledge extraction. Every test here
asserts the /api/documents or /api/search request/response CONTRACT (status
code + JSON shape) that the relocation (AE-0092 / AE-0093) must preserve
byte-for-byte. Each test references the Gherkin scenario it backs.

Feature files:
- tests/features/documents.feature
- tests/features/search.feature
- tests/features/agent_split/document_scope.feature (scope/namespace behavior,
  cross-referenced rather than duplicated here)

This module also captures the committed golden response snapshots under
tests/snapshots/knowledge/ via the _snapshot helper. Run with
``--snapshot-update`` (a flag added below) to regenerate them from the current,
pre-refactor behavior.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from rag_backend.domain.models import (
    Document,
    DocumentScope,
    DocumentStatus,
    SearchResult,
    User,
    UserRole,
)
from tests.integration.conftest import (
    TEST_SECRET,
    auth_headers_for,
    create_test_user,
)
from tests.snapshots.knowledge import _snapshot

if TYPE_CHECKING:
    from fastapi import FastAPI
    from httpx import Response
    from sqlalchemy.ext.asyncio import AsyncEngine

    from rag_backend.infrastructure.container import Container

# --- Constants -----------------------------------------------------------------
NONEXISTENT_UUID = "00000000-0000-0000-0000-000000000000"
SNAPSHOT_UPDATE_OPTION = "--snapshot-update"


@pytest.fixture
def snapshot_update(request: pytest.FixtureRequest) -> bool:
    """Whether snapshots should be written instead of asserted.

    Controlled by the ``--snapshot-update`` flag registered in
    ``tests/conftest.py``.
    """
    return bool(request.config.getoption(SNAPSHOT_UPDATE_OPTION))


# --- Client factory ------------------------------------------------------------
async def _make_engine() -> AsyncEngine:
    from sqlalchemy.ext.asyncio import create_async_engine

    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.infrastructure.database.config import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_config.c_engine = engine
    return engine


@pytest_asyncio.fixture
async def kb_env() -> AsyncGenerator[KnowledgeEnv, None]:
    """A shared in-memory DB + app environment with helpers to build clients.

    Exposes:
    - ``owner``: the default authenticated editor (the "caller").
    - ``client_for(user)``: an AsyncClient authenticated as ``user``.
    - ``anon_client()``: an unauthenticated AsyncClient.
    - ``seed_document(...)``: persist a document with a chosen owner/scope.
    - ``override_retriever(results)``: stub the hybrid retriever.
    """
    import rag_backend.infrastructure.database.config as db_config
    from rag_backend.api.app import create_app
    from rag_backend.infrastructure.container import get_container
    from rag_backend.infrastructure.database.config import close_db

    os.environ["SECRET_KEY"] = TEST_SECRET
    os.environ["ANON_SECRET_KEY"] = "test-anon-secret-for-integration-tests"

    engine = await _make_engine()
    owner = await create_test_user("kb-owner@integration.test", UserRole.EDITOR)
    app = create_app()
    container: Container = get_container()

    env = KnowledgeEnv(app=app, owner=owner, container=container)
    try:
        yield env
    finally:
        container.retriever.reset_override()
        container.vector_store.reset_override()
        db_config.c_engine = None
        await close_db()
        await engine.dispose()


class KnowledgeEnv:
    """Test environment with client + seeding helpers (see kb_env fixture)."""

    def __init__(self, app: FastAPI, owner: User, container: Container) -> None:
        self._app = app
        self.owner = owner
        self._container = container

    def client_for(self, user: User) -> AsyncClient:
        transport = ASGITransport(app=self._app)
        return AsyncClient(
            transport=transport,
            base_url="http://test",
            headers=auth_headers_for(user),
        )

    def anon_client(self) -> AsyncClient:
        transport = ASGITransport(app=self._app)
        return AsyncClient(transport=transport, base_url="http://test")

    async def make_user(self, email: str, role: UserRole) -> User:
        return await create_test_user(email, role)

    async def seed_document(
        self,
        owner_id: UUID,
        *,
        scope: DocumentScope = DocumentScope.PERSONAL,
        is_public: bool = False,
    ) -> Document:
        from rag_backend.infrastructure.database.config import get_session_maker

        session_maker = get_session_maker()
        async with session_maker() as session:
            repo = self._container.document_repository(session=session)
            document = Document(
                title="Seeded Document",
                content="Seeded content for the knowledge safety net.",
                metadata={"category": "seed"},
                scope=scope,
                is_public=is_public,
                owner_id=owner_id,
                status=DocumentStatus.COMPLETED,
            )
            created = await repo.create(document)
            await session.commit()
            return created

    def override_retriever(self, results: list[SearchResult]) -> None:
        retriever = AsyncMock()
        retriever.retrieve = AsyncMock(return_value=results)
        self._container.retriever.override(retriever)

    def override_vector_store(self) -> None:
        """Stub the vector store so delete/reprocess never call real Pinecone.

        ``document_pipeline`` is a Factory that resolves ``vector_store`` from
        this Singleton provider on each request, so overriding the provider
        applies to the request-scoped pipeline used by the route.
        """
        store = AsyncMock()
        store.delete_by_document = AsyncMock(return_value=None)
        store.upsert_chunks = AsyncMock(return_value=None)
        self._container.vector_store.override(store)


def _ranked_results() -> list[SearchResult]:
    """Deterministic ranked results for search-success scenarios."""
    return [
        SearchResult(
            content="Artificial intelligence is the simulation of human "
            "intelligence by machines.",
            document_id=UUID("11111111-1111-1111-1111-111111111111"),
            score=0.91,
            metadata={"title": "AI Overview"},
            rank=1,
        ),
        SearchResult(
            content="Machine learning is a subset of artificial intelligence.",
            document_id=UUID("22222222-2222-2222-2222-222222222222"),
            score=0.83,
            metadata={"title": "ML Basics"},
            rank=2,
        ),
    ]


# ==============================================================================
# Document endpoint scenarios (tests/features/documents.feature)
# ==============================================================================
class TestDocumentScopeContract:
    """Scope fields on the /api/documents create contract."""

    @pytest.mark.asyncio
    async def test_create_with_personal_scope(self, kb_env: KnowledgeEnv) -> None:
        """Scenario: Create document with explicit personal scope."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.post(
                "/api/documents",
                json={"title": "Doc", "content": "c", "scope": "personal"},
            )
        assert resp.status_code == 201
        body = resp.json()
        assert body["scope"] == "personal"
        assert body["is_public"] is False

    @pytest.mark.asyncio
    async def test_create_with_public_scope_and_flag(
        self, kb_env: KnowledgeEnv
    ) -> None:
        """Scenario: Create document with public scope and is_public flag."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.post(
                "/api/documents",
                json={
                    "title": "Doc",
                    "content": "c",
                    "scope": "public",
                    "is_public": True,
                },
            )
        assert resp.status_code == 201
        body = resp.json()
        assert body["scope"] == "public"
        assert body["is_public"] is True

    @pytest.mark.asyncio
    async def test_create_with_invalid_scope(self, kb_env: KnowledgeEnv) -> None:
        """Scenario: Create document with an invalid scope value."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.post(
                "/api/documents",
                json={"title": "Doc", "content": "c", "scope": "invalid"},
            )
        assert resp.status_code == 400
        assert "detail" in resp.json()

    @pytest.mark.asyncio
    async def test_create_defaults_to_personal_scope(
        self, kb_env: KnowledgeEnv
    ) -> None:
        """Scenario: Create document defaults to personal scope when scope omitted."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.post(
                "/api/documents", json={"title": "Doc", "content": "c"}
            )
        assert resp.status_code == 201
        assert resp.json()["scope"] == "personal"


class TestDocumentListingAccessControl:
    """Owner-vs-admin listing + pagination + validation."""

    @pytest.mark.asyncio
    async def test_owner_listing_excludes_other_users_docs(
        self, kb_env: KnowledgeEnv
    ) -> None:
        """Scenario: Listing returns only the caller's own documents (non-admin)."""
        other = await kb_env.make_user("kb-other@integration.test", UserRole.EDITOR)
        await kb_env.seed_document(other.id)
        async with kb_env.client_for(kb_env.owner) as client:
            await client.post("/api/documents", json={"title": "Mine", "content": "c"})
            resp = await client.get("/api/documents")
        assert resp.status_code == 200
        body = resp.json()
        titles = {item["title"] for item in body["items"]}
        assert "Mine" in titles
        assert "Seeded Document" not in titles

    @pytest.mark.asyncio
    async def test_admin_listing_includes_all_owners(
        self, kb_env: KnowledgeEnv
    ) -> None:
        """Scenario: Admin listing returns documents across all owners."""
        other = await kb_env.make_user("kb-other2@integration.test", UserRole.EDITOR)
        await kb_env.seed_document(other.id)
        admin = await kb_env.make_user("kb-admin@integration.test", UserRole.ADMIN)
        async with kb_env.client_for(admin) as client:
            resp = await client.get("/api/documents")
        assert resp.status_code == 200
        titles = {item["title"] for item in resp.json()["items"]}
        assert "Seeded Document" in titles

    @pytest.mark.asyncio
    async def test_listing_pagination(self, kb_env: KnowledgeEnv) -> None:
        """Scenario: Listing supports limit and offset pagination."""
        async with kb_env.client_for(kb_env.owner) as client:
            for index in range(3):
                await client.post(
                    "/api/documents", json={"title": f"Doc {index}", "content": "c"}
                )
            resp = await client.get("/api/documents", params={"limit": 1, "offset": 0})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) <= 1
        assert body["limit"] == 1
        assert body["offset"] == 0

    @pytest.mark.asyncio
    async def test_listing_rejects_out_of_range_limit(
        self, kb_env: KnowledgeEnv
    ) -> None:
        """Scenario: Listing rejects an out-of-range limit."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.get("/api/documents", params={"limit": 0})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_unauthenticated_listing_rejected(self, kb_env: KnowledgeEnv) -> None:
        """Scenario: Unauthenticated request to list documents is rejected."""
        async with kb_env.anon_client() as client:
            resp = await client.get("/api/documents")
        assert resp.status_code == 401


class TestDocumentOwnershipPermissions:
    """Non-owner permission boundaries on per-document endpoints."""

    @pytest.mark.asyncio
    async def test_non_owner_cannot_read(self, kb_env: KnowledgeEnv) -> None:
        """Scenario: Non-owner cannot read another user's document."""
        other = await kb_env.make_user("kb-o3@integration.test", UserRole.EDITOR)
        doc = await kb_env.seed_document(other.id, is_public=False)
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.get(f"/api/documents/{doc.id}")
        assert resp.status_code == 403
        assert "detail" in resp.json()

    @pytest.mark.asyncio
    async def test_non_owner_cannot_read_public_doc_of_other(
        self, kb_env: KnowledgeEnv
    ) -> None:
        """Scenario: Non-owner cannot read another user's document (is_public true).

        Current behavior: ownership check ignores is_public, so still 403.
        Cross-ref document_scope.feature for scope/namespace semantics.
        """
        other = await kb_env.make_user("kb-o4@integration.test", UserRole.EDITOR)
        doc = await kb_env.seed_document(
            other.id, scope=DocumentScope.PUBLIC, is_public=True
        )
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.get(f"/api/documents/{doc.id}")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_non_owner_cannot_read_status(self, kb_env: KnowledgeEnv) -> None:
        """Scenario: Non-owner cannot read another user's document status."""
        other = await kb_env.make_user("kb-o5@integration.test", UserRole.EDITOR)
        doc = await kb_env.seed_document(other.id)
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.get(f"/api/documents/{doc.id}/status")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_non_owner_cannot_delete(self, kb_env: KnowledgeEnv) -> None:
        """Scenario: Non-owner cannot delete another user's document."""
        other = await kb_env.make_user("kb-o6@integration.test", UserRole.EDITOR)
        doc = await kb_env.seed_document(other.id)
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.delete(f"/api/documents/{doc.id}")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_non_owner_cannot_reprocess(self, kb_env: KnowledgeEnv) -> None:
        """Scenario: Non-owner cannot reprocess another user's document."""
        other = await kb_env.make_user("kb-o7@integration.test", UserRole.EDITOR)
        doc = await kb_env.seed_document(other.id)
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.post(f"/api/documents/{doc.id}/reprocess")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_owner_can_read_own_document(self, kb_env: KnowledgeEnv) -> None:
        """Scenario: Owner can read their own document by ID."""
        doc = await kb_env.seed_document(kb_env.owner.id)
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.get(f"/api/documents/{doc.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == str(doc.id)

    @pytest.mark.asyncio
    async def test_get_malformed_id(self, kb_env: KnowledgeEnv) -> None:
        """Scenario: Get document with a malformed (non-UUID) ID."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.get("/api/documents/not-a-uuid")
        assert resp.status_code == 422


# ==============================================================================
# Search endpoint scenarios (tests/features/search.feature)
# ==============================================================================
class TestSearchContract:
    """Successful search response shape + bounds + auth."""

    @pytest.mark.asyncio
    async def test_post_search_success_shape(self, kb_env: KnowledgeEnv) -> None:
        """Scenario: Successful POST search returns the response contract shape."""
        kb_env.override_retriever(_ranked_results())
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.post(
                "/api/search", json={"query": "artificial intelligence"}
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["query"] == "artificial intelligence"
        assert isinstance(body["results"], list)
        assert body["total"] == len(body["results"])
        first = body["results"][0]
        for key in ("content", "document_id", "document_title", "score", "rank"):
            assert key in first

    @pytest.mark.asyncio
    async def test_get_search_success_shape(self, kb_env: KnowledgeEnv) -> None:
        """Scenario: Successful GET search returns the response contract shape."""
        kb_env.override_retriever(_ranked_results())
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.get("/api/search", params={"query": "test"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["query"] == "test"
        assert isinstance(body["results"], list)

    @pytest.mark.asyncio
    async def test_post_search_top_k_boundary(self, kb_env: KnowledgeEnv) -> None:
        """Scenario: POST search at the top_k boundary is accepted."""
        kb_env.override_retriever(_ranked_results())
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.post("/api/search", json={"query": "test", "top_k": 20})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_post_search_alpha_boundaries(self, kb_env: KnowledgeEnv) -> None:
        """Scenario: POST search at the alpha boundaries is accepted."""
        kb_env.override_retriever(_ranked_results())
        async with kb_env.client_for(kb_env.owner) as client:
            low = await client.post("/api/search", json={"query": "t", "alpha": 0.0})
            high = await client.post("/api/search", json={"query": "t", "alpha": 1.0})
        assert low.status_code == 200
        assert high.status_code == 200

    @pytest.mark.asyncio
    async def test_post_search_query_too_long(self, kb_env: KnowledgeEnv) -> None:
        """Scenario: POST search rejects a query over the maximum length."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.post("/api/search", json={"query": "x" * 1001})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_search_top_k_out_of_range(self, kb_env: KnowledgeEnv) -> None:
        """Scenario: GET search rejects out-of-range top_k."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.get(
                "/api/search", params={"query": "test", "top_k": 21}
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_search_alpha_out_of_range(self, kb_env: KnowledgeEnv) -> None:
        """Scenario: GET search rejects out-of-range alpha."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.get(
                "/api/search", params={"query": "test", "alpha": 1.5}
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_unauthenticated_post_search_rejected(
        self, kb_env: KnowledgeEnv
    ) -> None:
        """Scenario: Unauthenticated POST search is rejected."""
        async with kb_env.anon_client() as client:
            resp = await client.post("/api/search", json={"query": "test"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthenticated_get_search_rejected(
        self, kb_env: KnowledgeEnv
    ) -> None:
        """Scenario: Unauthenticated GET search is rejected."""
        async with kb_env.anon_client() as client:
            resp = await client.get("/api/search", params={"query": "test"})
        assert resp.status_code == 401


# ==============================================================================
# Golden snapshots — the enforceable byte-identical baseline (AE-0092/0093)
# ==============================================================================
class TestKnowledgeGoldenSnapshots:
    """Capture/diff committed golden snapshots for every documents+search route.

    With ``--snapshot-update`` these tests rewrite the committed snapshots from
    the current behavior. Without it, they assert the live response matches the
    committed snapshot (diff == 0).
    """

    async def _check(self, name: str, response: Response, *, update: bool) -> None:
        if update:
            _snapshot.write_snapshot(name, response)
            return
        _snapshot.assert_matches_snapshot(name, response)

    @pytest.mark.asyncio
    async def test_snapshot_create_document(
        self, kb_env: KnowledgeEnv, snapshot_update: bool
    ) -> None:
        """Golden: POST /api/documents (201)."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.post(
                "/api/documents",
                json={"title": "Snapshot Doc", "content": "snapshot content"},
            )
        await self._check("documents_create", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_create_document_validation_error(
        self, kb_env: KnowledgeEnv, snapshot_update: bool
    ) -> None:
        """Golden: POST /api/documents (422 validation)."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.post("/api/documents", json={"title": ""})
        await self._check(
            "documents_create_validation_error", resp, update=snapshot_update
        )

    @pytest.mark.asyncio
    async def test_snapshot_create_invalid_scope(
        self, kb_env: KnowledgeEnv, snapshot_update: bool
    ) -> None:
        """Golden: POST /api/documents (400 invalid scope)."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.post(
                "/api/documents",
                json={"title": "Doc", "content": "c", "scope": "invalid"},
            )
        await self._check(
            "documents_create_invalid_scope", resp, update=snapshot_update
        )

    @pytest.mark.asyncio
    async def test_snapshot_list_documents_empty(
        self, kb_env: KnowledgeEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /api/documents (200 empty)."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.get("/api/documents")
        await self._check("documents_list_empty", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_list_documents(
        self, kb_env: KnowledgeEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /api/documents (200 with one item)."""
        async with kb_env.client_for(kb_env.owner) as client:
            await client.post(
                "/api/documents",
                json={"title": "Listed Doc", "content": "c"},
            )
            resp = await client.get("/api/documents")
        await self._check("documents_list", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_get_document(
        self, kb_env: KnowledgeEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /api/documents/{id} (200)."""
        doc = await kb_env.seed_document(kb_env.owner.id)
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.get(f"/api/documents/{doc.id}")
        await self._check("documents_get", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_get_document_not_found(
        self, kb_env: KnowledgeEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /api/documents/{id} (404)."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.get(f"/api/documents/{NONEXISTENT_UUID}")
        await self._check("documents_get_not_found", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_get_document_status(
        self, kb_env: KnowledgeEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /api/documents/{id}/status (200)."""
        doc = await kb_env.seed_document(kb_env.owner.id)
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.get(f"/api/documents/{doc.id}/status")
        await self._check("documents_status", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_delete_document(
        self, kb_env: KnowledgeEnv, snapshot_update: bool
    ) -> None:
        """Golden: DELETE /api/documents/{id} (204)."""
        kb_env.override_vector_store()
        doc = await kb_env.seed_document(kb_env.owner.id)
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.delete(f"/api/documents/{doc.id}")
        await self._check("documents_delete", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_delete_document_not_found(
        self, kb_env: KnowledgeEnv, snapshot_update: bool
    ) -> None:
        """Golden: DELETE /api/documents/{id} (404)."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.delete(f"/api/documents/{NONEXISTENT_UUID}")
        await self._check("documents_delete_not_found", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_reprocess_not_found(
        self, kb_env: KnowledgeEnv, snapshot_update: bool
    ) -> None:
        """Golden: POST /api/documents/{id}/reprocess (404)."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.post(f"/api/documents/{NONEXISTENT_UUID}/reprocess")
        await self._check("documents_reprocess_not_found", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_upload_empty(
        self, kb_env: KnowledgeEnv, snapshot_update: bool
    ) -> None:
        """Golden: POST /api/documents/upload (400 empty file)."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.post(
                "/api/documents/upload",
                files={"file": ("empty.txt", b"", "text/plain")},
            )
        await self._check("documents_upload_empty", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_search_post(
        self, kb_env: KnowledgeEnv, snapshot_update: bool
    ) -> None:
        """Golden: POST /api/search (200)."""
        kb_env.override_retriever(_ranked_results())
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.post(
                "/api/search", json={"query": "artificial intelligence"}
            )
        await self._check("search_post", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_search_post_empty_results(
        self, kb_env: KnowledgeEnv, snapshot_update: bool
    ) -> None:
        """Golden: POST /api/search (200 with no results)."""
        kb_env.override_retriever([])
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.post("/api/search", json={"query": "nothing matches"})
        await self._check("search_post_empty", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_search_post_validation_error(
        self, kb_env: KnowledgeEnv, snapshot_update: bool
    ) -> None:
        """Golden: POST /api/search (422 empty query)."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.post("/api/search", json={"query": ""})
        await self._check("search_post_validation_error", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_search_get(
        self, kb_env: KnowledgeEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /api/search (200)."""
        kb_env.override_retriever(_ranked_results())
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.get("/api/search", params={"query": "test"})
        await self._check("search_get", resp, update=snapshot_update)

    @pytest.mark.asyncio
    async def test_snapshot_search_get_validation_error(
        self, kb_env: KnowledgeEnv, snapshot_update: bool
    ) -> None:
        """Golden: GET /api/search (422 empty query)."""
        async with kb_env.client_for(kb_env.owner) as client:
            resp = await client.get("/api/search", params={"query": ""})
        await self._check("search_get_validation_error", resp, update=snapshot_update)
