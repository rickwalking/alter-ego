"""PostgreSQL user repository implementation."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.models import User, UserRole
from rag_backend.domain.protocols import UserRepository
from rag_backend.infrastructure.database.models import UserModel


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
        """Update an existing user.

        Args:
            user: User entity with updated fields.

        Returns:
            Updated user entity.
        """
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == str(user.id))
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"User with id {user.id} not found")

        model.email = user.email
        model.full_name = user.full_name
        model.hashed_password = user.hashed_password
        model.role = user.role.value
        model.is_active = user.is_active
        model.updated_at = user.updated_at

        await self._session.flush()
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
        result = await self._session.execute(select(func.count()).select_from(UserModel))
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
