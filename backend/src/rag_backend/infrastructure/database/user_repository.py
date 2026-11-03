"""PostgreSQL user repository implementation."""

from collections.abc import Callable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.models import User, UserField, UserRole
from rag_backend.domain.protocols import UserRepository
from rag_backend.infrastructure.database.models import UserModel

_COLUMN_VALUES: dict[UserField, Callable[[User], object]] = {
    UserField.EMAIL: lambda user: user.email,
    UserField.FULL_NAME: lambda user: user.full_name,
    UserField.CREDENTIAL_HASH: lambda user: user.hashed_password,
    UserField.ROLE: lambda user: user.role.value,
    UserField.IS_ACTIVE: lambda user: user.is_active,
    UserField.CREDENTIAL_CHANGE_REQUIRED: lambda user: user.must_change_password,
    UserField.SESSION_VERSION: lambda user: user.token_version,
    UserField.UPDATED_AT: lambda user: user.updated_at,
}


class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of UserRepository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session.

        Args:
            session: SQLAlchemy async session.
        """
        self._session = session

    async def create(self, user: User) -> User:
        """Create a new user.

        Args:
            user: User entity to create.

        Returns:
            Created user with assigned ID.
        """
        model = UserModel.from_entity(user)
        self._session.add(model)
        await self._session.flush()
        return model.to_entity()

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get a user by ID.

        Args:
            user_id: User UUID.

        Returns:
            User entity if found, None otherwise.
        """
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == str(user_id))
        )
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def get_by_id_for_update(self, user_id: UUID) -> User | None:
        """Get a user by ID, locking its row until the transaction ends.

        The row is re-read even when the session already holds it, so a
        concurrent change committed meanwhile (a new hash, a bumped token
        version) is what the caller sees. SQLite ignores the lock.
        """
        result = await self._session.execute(
            select(UserModel)
            .where(UserModel.id == str(user_id))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def get_by_email(self, email: str) -> User | None:
        """Get a user by email address.

        Args:
            email: User email.

        Returns:
            User entity if found, None otherwise.
        """
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        model = result.scalar_one_or_none()
        return model.to_entity() if model else None

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[User]:
        """Get all users ordered by created_at desc.

        Args:
            limit: Maximum number of users to return.
            offset: Number of users to skip.

        Returns:
            List of user entities.
        """
        result = await self._session.execute(
            select(UserModel)
            .order_by(UserModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [m.to_entity() for m in result.scalars().all()]

    async def update(self, user: User) -> User:
        """Save the fields of ``user`` that changed, and only those.

        Only ``user.changed_fields()`` are written, so a save from an entity
        read earlier never puts back a column it did not change (a password
        hash or token version committed meanwhile survives a profile edit).
        When ``updated_at`` is not written the column's ``onupdate`` sets it in
        the database and the flush expires it; the model is refreshed before
        mapping so the entity never triggers a lazy load inside the async
        session (that lazy load raised ``MissingGreenlet`` → HTTP 500).

        Args:
            user: User entity with updated fields.

        Returns:
            Updated user entity, as stored.
        """
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == str(user.id))
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"User with id {user.id} not found")

        for changed in user.changed_fields():
            setattr(model, changed.value, _COLUMN_VALUES[changed](user))

        await self._session.flush()
        await self._session.refresh(model)
        return model.to_entity()

    async def delete(self, user_id: UUID) -> bool:
        """Delete a user by ID.

        Args:
            user_id: User UUID.

        Returns:
            True if deleted, False if not found.
        """
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == str(user_id))
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False

        await self._session.delete(model)
        await self._session.flush()
        return True

    async def count(self) -> int:
        """Count all users.

        Returns:
            Total number of users.
        """
        result = await self._session.execute(
            select(func.count()).select_from(UserModel)
        )
        return result.scalar() or 0

    async def count_by_role(self, role: UserRole) -> int:
        """Count users with a specific role.

        Args:
            role: User role to filter by.

        Returns:
            Number of users with the given role.
        """
        result = await self._session.execute(
            select(func.count())
            .select_from(UserModel)
            .where(UserModel.role == role.value)
        )
        return result.scalar() or 0

    async def count_active_by_role(self, role: UserRole) -> int:
        """Count the active users with a specific role, locking their rows.

        The rows are selected ``FOR UPDATE`` (Postgres refuses it on
        ``count(*)``, so the ids are counted here) and stay locked until the
        transaction ends, in id order so two transactions lock them in the same
        order. Two admins deactivating each other at once are then
        serialized: the second waits, re-reads after the first commits and sees
        one active admin, so the last-admin guard refuses it. SQLite ignores the
        lock.

        Args:
            role: User role to filter by.

        Returns:
            Number of active users with the given role.
        """
        result = await self._session.execute(
            select(UserModel.id)
            .where(UserModel.role == role.value, UserModel.is_active.is_(True))
            .order_by(UserModel.id)
            .with_for_update()
        )
        return len(result.scalars().all())
