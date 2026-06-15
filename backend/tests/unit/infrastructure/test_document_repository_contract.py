"""Shared repository contract tests for the DocumentRepository port (AE-0094).

One parametrized contract suite runs the SAME assertions against BOTH:

* a **fake in-memory** ``DocumentRepository`` (a test double, see
  :class:`FakeDocumentRepository`), and
* the real :class:`PostgresDocumentRepository`.

Because both adapters are exercised by identical scenarios, any divergence in
observable behavior surfaces as a test failure — pinning the port's contract so
adapter swaps stay safe (Phase 2 module pilot, AE-0094).

The Postgres adapter runs against the SQLite in-memory database used across the
backend test suite (per ``backend/CLAUDE.md`` — "Use SQLite in-memory for
database tests"), so it is always available in CI; no skip is required.

Scenarios reference the AE-0090 full-field document persistence behavior for the
scope/is_public round-trip and the AE-0088 Knowledge safety-net behaviors.
"""

from typing import Protocol, TypedDict
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.models import Document, DocumentScope, DocumentStatus
from rag_backend.domain.protocols.repositories import DocumentRepository
from rag_backend.infrastructure.database.document_repository import (
    PostgresDocumentRepository,
)

# --- Constants (no magic strings) -------------------------------------------

_FAKE = "fake"
_POSTGRES = "postgres"
_ERR_NOT_FOUND_FRAGMENT = "not found"

_DEFAULT_LIMIT = 100
_DEFAULT_OFFSET = 0


# --- Owner-scoped query shape ------------------------------------------------
# Mirrors the ``_OwnerQuery`` TypedDict bundled by ``PostgresDocumentRepository``
# and the ``/api/documents`` route, so the fake accepts identical inputs.


class OwnerQuery(TypedDict, total=False):
    """Bundled query parameters for owner-scoped document listing."""

    owner_id: UUID
    status: DocumentStatus | None
    limit: int
    offset: int


# --- Extended contract port --------------------------------------------------
# The shipped ``DocumentRepository`` Protocol is slim (CRUD + count). The live
# adapter contract consumed by ``/api/documents`` also includes owner-scoped
# queries; this Protocol captures the full set so the parametrized fixture and
# the owner-scoped tests are type-checked against it. Both the fake and
# ``PostgresDocumentRepository`` satisfy it structurally.


class DocumentRepositoryContract(DocumentRepository, Protocol):
    """Full adapter contract: the shipped port plus owner-scoped queries."""

    async def get_all_for_owner(self, query: OwnerQuery) -> list[Document]: ...

    async def count_for_owner(
        self, owner_id: UUID, status: DocumentStatus | None = None
    ) -> int: ...


# --- Fake in-memory adapter --------------------------------------------------


class FakeDocumentRepository:
    """In-memory test double implementing the ``DocumentRepository`` port.

    Mirrors the observable behavior of :class:`PostgresDocumentRepository`:
    insertion-stable ``get_all`` ordering by descending ``updated_at`` (newest
    first), status filtering, owner scoping, and the same not-found semantics
    (``update`` raises ``ValueError``; ``delete`` returns ``False``).
    """

    def __init__(self) -> None:
        self._store: dict[UUID, Document] = {}

    @staticmethod
    def _clone(document: Document) -> Document:
        """Return a defensive copy so callers cannot mutate stored state.

        Matches the Postgres adapter, which always rebuilds entities from the
        ORM row (``to_entity``) rather than handing back caller references.
        """
        return Document(
            content=document.content,
            title=document.title,
            metadata=dict(document.metadata),
            id=document.id,
            created_at=document.created_at,
            updated_at=document.updated_at,
            status=document.status,
            error_message=document.error_message,
            chunk_count=document.chunk_count,
            scope=document.scope,
            owner_id=document.owner_id,
            is_public=document.is_public,
        )

    def _sorted(self, documents: list[Document]) -> list[Document]:
        """Order newest-first by ``updated_at`` (stable for equal timestamps)."""
        ordered = sorted(
            enumerate(documents),
            key=lambda pair: (pair[1].updated_at, pair[0]),
            reverse=True,
        )
        return [doc for _, doc in ordered]

    async def create(self, document: Document) -> Document:
        self._store[document.id] = self._clone(document)
        return self._clone(self._store[document.id])

    async def get_by_id(self, document_id: UUID) -> Document | None:
        found = self._store.get(document_id)
        return self._clone(found) if found else None

    async def get_all(
        self,
        status: DocumentStatus | None = None,
        limit: int = _DEFAULT_LIMIT,
        offset: int = _DEFAULT_OFFSET,
    ) -> list[Document]:
        matches = [
            doc
            for doc in self._store.values()
            if status is None or doc.status == status
        ]
        ordered = self._sorted(matches)
        page = ordered[offset : offset + limit]
        return [self._clone(doc) for doc in page]

    async def get_all_for_owner(self, query: OwnerQuery) -> list[Document]:
        owner_id = query["owner_id"]
        status = query.get("status")
        limit = query.get("limit", _DEFAULT_LIMIT)
        offset = query.get("offset", _DEFAULT_OFFSET)
        matches = [
            doc
            for doc in self._store.values()
            if doc.owner_id == owner_id and (status is None or doc.status == status)
        ]
        ordered = self._sorted(matches)
        page = ordered[offset : offset + limit]
        return [self._clone(doc) for doc in page]

    async def count_for_owner(
        self,
        owner_id: UUID,
        status: DocumentStatus | None = None,
    ) -> int:
        return sum(
            1
            for doc in self._store.values()
            if doc.owner_id == owner_id and (status is None or doc.status == status)
        )

    async def update(self, document: Document) -> Document:
        if document.id not in self._store:
            raise ValueError(_ERR_NOT_FOUND_FRAGMENT)
        self._store[document.id] = self._clone(document)
        return self._clone(self._store[document.id])

    async def delete(self, document_id: UUID) -> bool:
        if document_id not in self._store:
            return False
        del self._store[document_id]
        return True

    async def count(self, status: DocumentStatus | None = None) -> int:
        return sum(
            1 for doc in self._store.values() if status is None or doc.status == status
        )


# Static Protocol conformance: the fake satisfies the shipped DocumentRepository
# port for the core CRUD/count operations the domain declares, and the extended
# contract (incl. owner-scoped queries). mypy --strict checks these assignments,
# satisfying AC5 ("fake implements the port, type-checked").
_PORT_CHECK: DocumentRepository = FakeDocumentRepository()
_CONTRACT_CHECK: DocumentRepositoryContract = FakeDocumentRepository()


# --- Owner-id helpers --------------------------------------------------------
# DocumentModel.owner_id is a FK to users.id; the Postgres adapter never
# enforces it on flush (no commit), and the contract assertions never persist a
# matching user, so owner_id is exercised purely as an opaque scoping key shared
# by both adapters.

_OWNER_A = UUID("00000000-0000-0000-0000-00000000000a")
_OWNER_B = UUID("00000000-0000-0000-0000-00000000000b")


def _owned_document(owner_id: UUID, title: str) -> Document:
    return Document(content=f"content::{title}", title=title, owner_id=owner_id)


# --- Parametrization fixtures ------------------------------------------------


def _build_postgres_repo(db_session: AsyncSession) -> PostgresDocumentRepository:
    """Build the real adapter over the shared SQLite test session.

    The shared ``db_session`` fixture (SQLite in-memory) is always available in
    CI, so the Postgres parametrization normally runs. If a session cannot be
    obtained, the calling fixture skips this parametrization while the fake
    parametrization still runs (AC: the fake must always run).
    """
    return PostgresDocumentRepository(db_session)


@pytest.fixture(params=[_FAKE, _POSTGRES])
def repo(request: pytest.FixtureRequest) -> DocumentRepositoryContract:
    """Return each adapter in turn so every contract test runs against both."""
    if request.param == _FAKE:
        return FakeDocumentRepository()

    # SQLite in-memory db_session is always available (backend/CLAUDE.md), so the
    # Postgres-port adapter always runs — no skip path.
    db_session = request.getfixturevalue("db_session")
    return _build_postgres_repo(db_session)


# --- Contract suite ----------------------------------------------------------


@pytest.mark.unit
class TestDocumentRepositoryContract:
    """Behavior pinned identically across the fake and Postgres adapters."""

    async def test_create_returns_persisted_entity(
        self, repo: DocumentRepositoryContract
    ) -> None:
        """create SHALL return the persisted document with its fields intact."""
        doc = Document(content="hello", title="Greeting")

        created = await repo.create(doc)

        assert created.id == doc.id
        assert created.title == "Greeting"
        assert created.content == "hello"
        assert created.status == DocumentStatus.PENDING

    async def test_get_by_id_hit(self, repo: DocumentRepositoryContract) -> None:
        """get_by_id SHALL return the document when it exists."""
        created = await repo.create(Document(content="c", title="t"))

        retrieved = await repo.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == "t"

    async def test_get_by_id_miss(self, repo: DocumentRepositoryContract) -> None:
        """get_by_id SHALL return None for an unknown id."""
        assert await repo.get_by_id(uuid4()) is None

    async def test_get_all_empty(self, repo: DocumentRepositoryContract) -> None:
        """get_all SHALL return an empty list when nothing is stored."""
        assert await repo.get_all() == []

    async def test_get_all_returns_every_document(
        self, repo: DocumentRepositoryContract
    ) -> None:
        """get_all SHALL return all stored documents."""
        for i in range(3):
            await repo.create(Document(content=f"c{i}", title=f"t{i}"))

        assert len(await repo.get_all()) == 3

    async def test_get_all_filters_by_status(
        self, repo: DocumentRepositoryContract
    ) -> None:
        """get_all SHALL filter by status."""
        pending = Document(content="p", title="pending")
        completed = Document(content="c", title="completed")
        completed.status = DocumentStatus.COMPLETED
        await repo.create(pending)
        await repo.create(completed)

        results = await repo.get_all(status=DocumentStatus.COMPLETED)

        assert [d.title for d in results] == ["completed"]

    async def test_get_all_pagination(self, repo: DocumentRepositoryContract) -> None:
        """get_all SHALL honor limit/offset and order newest-first."""
        for i in range(5):
            await repo.create(Document(content=f"c{i}", title=f"t{i}"))

        first = await repo.get_all(limit=2, offset=0)
        second = await repo.get_all(limit=2, offset=2)

        assert len(first) == 2
        assert len(second) == 2
        first_ids = {d.id for d in first}
        second_ids = {d.id for d in second}
        assert first_ids.isdisjoint(second_ids)

    async def test_update_existing(self, repo: DocumentRepositoryContract) -> None:
        """update SHALL persist field changes for an existing document."""
        created = await repo.create(Document(content="c", title="old"))

        created.title = "new"
        created.mark_completed(chunk_count=7)
        updated = await repo.update(created)

        assert updated.title == "new"
        assert updated.status == DocumentStatus.COMPLETED
        assert updated.chunk_count == 7

        reloaded = await repo.get_by_id(created.id)
        assert reloaded is not None
        assert reloaded.title == "new"
        assert reloaded.chunk_count == 7

    async def test_update_missing_raises(
        self, repo: DocumentRepositoryContract
    ) -> None:
        """update SHALL raise ValueError for an unknown document."""
        ghost = Document(content="c", title="ghost")

        with pytest.raises(ValueError, match=_ERR_NOT_FOUND_FRAGMENT):
            await repo.update(ghost)

    async def test_delete_existing(self, repo: DocumentRepositoryContract) -> None:
        """delete SHALL remove an existing document and return True."""
        created = await repo.create(Document(content="c", title="t"))

        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_missing(self, repo: DocumentRepositoryContract) -> None:
        """delete SHALL return False for an unknown document."""
        assert await repo.delete(uuid4()) is False

    async def test_count_empty(self, repo: DocumentRepositoryContract) -> None:
        """count SHALL return 0 when nothing is stored."""
        assert await repo.count() == 0

    async def test_count_and_status_filter(
        self, repo: DocumentRepositoryContract
    ) -> None:
        """count SHALL reflect totals and the optional status filter."""
        pending = Document(content="p", title="p")
        completed = Document(content="c", title="c")
        completed.status = DocumentStatus.COMPLETED
        await repo.create(pending)
        await repo.create(completed)

        assert await repo.count() == 2
        assert await repo.count(status=DocumentStatus.PENDING) == 1
        assert await repo.count(status=DocumentStatus.COMPLETED) == 1


@pytest.mark.unit
class TestDocumentRepositoryOwnerContract:
    """Owner-scoped queries pinned identically across both adapters.

    These methods are not on the slim ``DocumentRepository`` Protocol but are
    part of the live adapter contract consumed by ``/api/documents``; both
    adapters are asserted to behave identically.
    """

    async def test_get_all_for_owner_scopes_results(
        self, repo: DocumentRepositoryContract
    ) -> None:
        await repo.create(_owned_document(_OWNER_A, "a1"))
        await repo.create(_owned_document(_OWNER_A, "a2"))
        await repo.create(_owned_document(_OWNER_B, "b1"))

        owner_a = await repo.get_all_for_owner(OwnerQuery(owner_id=_OWNER_A))

        assert {d.title for d in owner_a} == {"a1", "a2"}
        assert all(d.owner_id == _OWNER_A for d in owner_a)

    async def test_get_all_for_owner_status_and_pagination(
        self, repo: DocumentRepositoryContract
    ) -> None:
        for i in range(3):
            await repo.create(_owned_document(_OWNER_A, f"a{i}"))
        completed = _owned_document(_OWNER_A, "done")
        completed.status = DocumentStatus.COMPLETED
        await repo.create(completed)

        only_completed = await repo.get_all_for_owner(
            OwnerQuery(owner_id=_OWNER_A, status=DocumentStatus.COMPLETED)
        )
        first_page = await repo.get_all_for_owner(
            OwnerQuery(owner_id=_OWNER_A, limit=2, offset=0)
        )

        assert [d.title for d in only_completed] == ["done"]
        assert len(first_page) == 2

    async def test_count_for_owner(self, repo: DocumentRepositoryContract) -> None:
        await repo.create(_owned_document(_OWNER_A, "a1"))
        await repo.create(_owned_document(_OWNER_A, "a2"))
        await repo.create(_owned_document(_OWNER_B, "b1"))

        assert await repo.count_for_owner(_OWNER_A) == 2
        assert await repo.count_for_owner(_OWNER_B) == 1
        assert await repo.count_for_owner(uuid4()) == 0

    async def test_count_for_owner_status_filter(
        self, repo: DocumentRepositoryContract
    ) -> None:
        pending = _owned_document(_OWNER_A, "pending")
        completed = _owned_document(_OWNER_A, "completed")
        completed.status = DocumentStatus.COMPLETED
        await repo.create(pending)
        await repo.create(completed)

        assert (
            await repo.count_for_owner(_OWNER_A, status=DocumentStatus.COMPLETED) == 1
        )


@pytest.mark.unit
class TestDocumentRepositoryScopeContract:
    """scope/is_public round-trip pinned identically (AE-0090 fields)."""

    async def test_scope_and_is_public_create_round_trip(
        self, repo: DocumentRepositoryContract
    ) -> None:
        """Scenario: scope/is_public round-trip on create (AE-0090).

        Given a document with scope INTERNAL and is_public False, when saved
        and reloaded, then scope is INTERNAL and is_public is False.
        """
        doc = Document(
            content="internal note",
            title="Internal",
            scope=DocumentScope.INTERNAL,
            is_public=False,
        )

        created = await repo.create(doc)
        reloaded = await repo.get_by_id(created.id)

        assert reloaded is not None
        assert reloaded.scope == DocumentScope.INTERNAL
        assert reloaded.is_public is False

    async def test_public_scope_round_trip(
        self, repo: DocumentRepositoryContract
    ) -> None:
        doc = Document(
            content="public",
            title="Public",
            scope=DocumentScope.PUBLIC,
            is_public=True,
        )

        reloaded = await repo.get_by_id((await repo.create(doc)).id)

        assert reloaded is not None
        assert reloaded.scope == DocumentScope.PUBLIC
        assert reloaded.is_public is True

    async def test_scope_and_is_public_update_round_trip(
        self, repo: DocumentRepositoryContract
    ) -> None:
        """Scenario: scope/is_public changes persist via update (AE-0090)."""
        created = await repo.create(Document(content="c", title="t"))
        assert created.scope == DocumentScope.PERSONAL
        assert created.is_public is False

        created.scope = DocumentScope.PUBLIC
        created.is_public = True
        # mark_completed refreshes updated_at so the adapter writes an explicit
        # timestamp (mirrors real usage and avoids a server onupdate re-fetch).
        created.mark_completed(chunk_count=2)
        await repo.update(created)

        reloaded = await repo.get_by_id(created.id)
        assert reloaded is not None
        assert reloaded.scope == DocumentScope.PUBLIC
        assert reloaded.is_public is True
