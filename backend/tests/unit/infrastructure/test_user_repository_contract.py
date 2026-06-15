"""Shared repository contract tests for the UserRepository port (AE-0098).

One parametrized contract suite runs the SAME assertions against BOTH:

* a **fake in-memory** ``UserRepository`` (a test double, see
  :class:`FakeUserRepository`), and
* the real :class:`PostgresUserRepository`.

Because both adapters are exercised by identical scenarios, any divergence in
observable behavior surfaces as a test failure — pinning the port's contract so
adapter swaps stay safe (mirrors the AE-0094 ``DocumentRepository`` contract).

The Postgres adapter runs against the SQLite in-memory database used across the
backend test suite (per ``backend/CLAUDE.md`` — "Use SQLite in-memory for
database tests"), so it is always available in CI; no skip is required.

The contract also proves the AE-0098 **object-identity shim**: the
``UserRepository`` re-exported by the identity module is the IDENTICAL Protocol
object as the legacy ``domain.protocols.repositories.UserRepository``, so
existing callers keep resolving.
"""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.models import User, UserRole
from rag_backend.domain.protocols.repositories import (
    UserRepository as LegacyUserRepository,
)
from rag_backend.infrastructure.database.user_repository import PostgresUserRepository
from rag_backend.modules.identity.domain.ports import (
    UserRepository as ModuleUserRepository,
)

# --- Constants (no magic strings) -------------------------------------------

_FAKE = "fake"
_POSTGRES = "postgres"
_ERR_NOT_FOUND_FRAGMENT = "not found"

_DEFAULT_LIMIT = 100
_DEFAULT_OFFSET = 0


# --- Object-identity shim (AE-0098 AC) ---------------------------------------
# The identity module re-exports the SAME Protocol object, never a copy, so the
# ~50+ legacy callers of ``domain.protocols.repositories.UserRepository`` keep
# resolving to the identical object after the shim lands.
_SHIM_IDENTITY: bool = LegacyUserRepository is ModuleUserRepository


# --- Fake in-memory adapter --------------------------------------------------


class FakeUserRepository:
    """In-memory test double implementing the ``UserRepository`` port.

    Mirrors the observable behavior of :class:`PostgresUserRepository`:
    ``get_all`` ordered newest-first by ``created_at``, email lookup, and the
    same not-found semantics (``update`` raises ``ValueError``; ``delete``
    returns ``False``).
    """

    def __init__(self) -> None:
        self._store: dict[UUID, User] = {}

    @staticmethod
    def _clone(user: User) -> User:
        """Return a defensive copy so callers cannot mutate stored state.

        Matches the Postgres adapter, which always rebuilds entities from the
        ORM row (``to_entity``) rather than handing back caller references.
        """
        return User(
            email=user.email,
            full_name=user.full_name,
            hashed_password=user.hashed_password,
            role=user.role,
            is_active=user.is_active,
            id=user.id,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    async def create(self, user: User) -> User:
        self._store[user.id] = self._clone(user)
        return self._clone(self._store[user.id])

    async def get_by_id(self, user_id: UUID) -> User | None:
        found = self._store.get(user_id)
        return self._clone(found) if found else None

    async def get_by_email(self, email: str) -> User | None:
        for user in self._store.values():
            if user.email == email:
                return self._clone(user)
        return None

    async def get_all(
        self, limit: int = _DEFAULT_LIMIT, offset: int = _DEFAULT_OFFSET
    ) -> list[User]:
        ordered = sorted(
            enumerate(self._store.values()),
            key=lambda pair: (pair[1].created_at, pair[0]),
            reverse=True,
        )
        page = [user for _, user in ordered][offset : offset + limit]
        return [self._clone(user) for user in page]

    async def update(self, user: User) -> User:
        if user.id not in self._store:
            raise ValueError(_ERR_NOT_FOUND_FRAGMENT)
        self._store[user.id] = self._clone(user)
        return self._clone(self._store[user.id])

    async def delete(self, user_id: UUID) -> bool:
        if user_id not in self._store:
            return False
        del self._store[user_id]
        return True

    async def count(self) -> int:
        return len(self._store)

    async def count_by_role(self, role: UserRole) -> int:
        return sum(1 for user in self._store.values() if user.role == role)


# Static Protocol conformance: the fake satisfies the shipped UserRepository
# port. mypy --strict checks this assignment, satisfying the AC that the fake
# implements the port and is type-checked.
_PORT_CHECK: ModuleUserRepository = FakeUserRepository()


# --- Test data helpers -------------------------------------------------------


def _user(email: str, role: UserRole = UserRole.EDITOR) -> User:
    return User(
        email=email,
        full_name=email.split("@")[0],
        hashed_password="hashed::" + email,
        role=role,
    )


# --- Parametrization fixtures ------------------------------------------------


@pytest.fixture(params=[_FAKE, _POSTGRES])
def repo(request: pytest.FixtureRequest) -> ModuleUserRepository:
    """Return each adapter in turn so every contract test runs against both."""
    if request.param == _FAKE:
        return FakeUserRepository()

    # SQLite in-memory db_session is always available (backend/CLAUDE.md), so the
    # Postgres-port adapter always runs — no skip path.
    db_session: AsyncSession = request.getfixturevalue("db_session")
    return PostgresUserRepository(db_session)


# --- Contract suite ----------------------------------------------------------


@pytest.mark.unit
class TestUserRepositoryShim:
    """The identity-module port is the identical object as the legacy port."""

    def test_object_identity_shim(self) -> None:
        """The re-export SHALL be the SAME Protocol object (no copy)."""
        assert _SHIM_IDENTITY is True
        assert LegacyUserRepository is ModuleUserRepository


@pytest.mark.unit
class TestUserRepositoryContract:
    """Behavior pinned identically across the fake and Postgres adapters."""

    async def test_create_returns_persisted_entity(
        self, repo: ModuleUserRepository
    ) -> None:
        """create SHALL return the persisted user with its fields intact."""
        user = _user("alice@example.com")

        created = await repo.create(user)

        assert created.id == user.id
        assert created.email == "alice@example.com"
        assert created.role == UserRole.EDITOR
        assert created.is_active is True

    async def test_get_by_id_hit(self, repo: ModuleUserRepository) -> None:
        """get_by_id SHALL return the user when it exists."""
        created = await repo.create(_user("bob@example.com"))

        retrieved = await repo.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.email == "bob@example.com"

    async def test_get_by_id_miss(self, repo: ModuleUserRepository) -> None:
        """get_by_id SHALL return None for an unknown id."""
        assert await repo.get_by_id(uuid4()) is None

    async def test_get_by_email_hit(self, repo: ModuleUserRepository) -> None:
        """get_by_email SHALL return the user matching the email."""
        await repo.create(_user("carol@example.com"))

        found = await repo.get_by_email("carol@example.com")

        assert found is not None
        assert found.email == "carol@example.com"

    async def test_get_by_email_miss(self, repo: ModuleUserRepository) -> None:
        """get_by_email SHALL return None for an unknown email."""
        assert await repo.get_by_email("nobody@example.com") is None

    async def test_get_all_empty(self, repo: ModuleUserRepository) -> None:
        """get_all SHALL return an empty list when nothing is stored."""
        assert await repo.get_all() == []

    async def test_get_all_returns_every_user(self, repo: ModuleUserRepository) -> None:
        """get_all SHALL return all stored users."""
        for i in range(3):
            await repo.create(_user(f"user{i}@example.com"))

        assert len(await repo.get_all()) == 3

    async def test_get_all_pagination(self, repo: ModuleUserRepository) -> None:
        """get_all SHALL honor limit/offset with disjoint pages."""
        for i in range(5):
            await repo.create(_user(f"page{i}@example.com"))

        first = await repo.get_all(limit=2, offset=0)
        second = await repo.get_all(limit=2, offset=2)

        assert len(first) == 2
        assert len(second) == 2
        assert {u.id for u in first}.isdisjoint({u.id for u in second})

    async def test_update_existing(self, repo: ModuleUserRepository) -> None:
        """update SHALL persist field changes for an existing user."""
        created = await repo.create(_user("dave@example.com"))

        created.full_name = "Dave Updated"
        created.set_role(UserRole.ADMIN)
        updated = await repo.update(created)

        assert updated.full_name == "Dave Updated"
        assert updated.role == UserRole.ADMIN

        reloaded = await repo.get_by_id(created.id)
        assert reloaded is not None
        assert reloaded.full_name == "Dave Updated"
        assert reloaded.role == UserRole.ADMIN

    async def test_update_missing_raises(self, repo: ModuleUserRepository) -> None:
        """update SHALL raise ValueError for an unknown user."""
        ghost = _user("ghost@example.com")

        with pytest.raises(ValueError, match=_ERR_NOT_FOUND_FRAGMENT):
            await repo.update(ghost)

    async def test_delete_existing(self, repo: ModuleUserRepository) -> None:
        """delete SHALL remove an existing user and return True."""
        created = await repo.create(_user("erin@example.com"))

        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_missing(self, repo: ModuleUserRepository) -> None:
        """delete SHALL return False for an unknown user."""
        assert await repo.delete(uuid4()) is False

    async def test_count_empty(self, repo: ModuleUserRepository) -> None:
        """count SHALL return 0 when nothing is stored."""
        assert await repo.count() == 0

    async def test_count_reflects_total(self, repo: ModuleUserRepository) -> None:
        """count SHALL reflect the number of stored users."""
        await repo.create(_user("a@example.com"))
        await repo.create(_user("b@example.com"))

        assert await repo.count() == 2

    async def test_count_by_role(self, repo: ModuleUserRepository) -> None:
        """count_by_role SHALL count only users with the given role."""
        await repo.create(_user("admin1@example.com", role=UserRole.ADMIN))
        await repo.create(_user("editor1@example.com", role=UserRole.EDITOR))
        await repo.create(_user("editor2@example.com", role=UserRole.EDITOR))

        assert await repo.count_by_role(UserRole.ADMIN) == 1
        assert await repo.count_by_role(UserRole.EDITOR) == 2
