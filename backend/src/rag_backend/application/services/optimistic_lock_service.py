"""Optimistic locking for concurrent edit prevention (WF-005)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.optimistic_locking import (
    DEFAULT_LOCK_TTL_SECONDS,
    ERR_LOCK_HELD_BY_OTHER,
    ERR_VERSION_CONFLICT,
)
from rag_backend.infrastructure.database.models.content_lock import ContentLockModel


class OptimisticLockService:
    """Version checks and short-lived edit locks."""

    async def check_version(
        self,
        current_version: int,
        expected_version: int | None,
    ) -> None:
        """Raise if expected version does not match current."""
        if expected_version is None:
            return
        if expected_version != current_version:
            raise ValueError(ERR_VERSION_CONFLICT)

    async def apply_versioned_update(
        self,
        db: AsyncSession,
        *,
        post_id: str,
        expected_version: int,
        values: dict[str, object],
    ) -> None:
        """Atomically apply blog post updates when lock_version matches."""
        from sqlalchemy import update

        from rag_backend.infrastructure.database.models.blog_post import BlogPostModel

        assignment = {**values, "lock_version": expected_version + 1}
        result = await db.execute(
            update(BlogPostModel)
            .where(
                BlogPostModel.id == post_id,
                BlogPostModel.lock_version == expected_version,
            )
            .values(**assignment)
        )
        if result.rowcount != 1:
            raise ValueError(ERR_VERSION_CONFLICT)

    async def acquire_lock(
        self,
        db: AsyncSession,
        *,
        content_id: str,
        content_type: str,
        user_id: str,
        user_name: str,
        ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
    ) -> ContentLockModel:
        """Acquire or refresh an edit lock."""
        await self._expire_stale_locks(db)
        existing = await self._get_lock(db, content_id, content_type)
        if existing is not None and existing.user_id != user_id:
            raise ValueError(ERR_LOCK_HELD_BY_OTHER)
        expires = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        if existing is not None:
            existing.expires_at = expires
            existing.user_name = user_name
            await db.flush()
            return existing
        lock = ContentLockModel(
            content_id=content_id,
            content_type=content_type,
            user_id=user_id,
            user_name=user_name,
            expires_at=expires,
        )
        db.add(lock)
        await db.flush()
        return lock

    async def release_lock(
        self,
        db: AsyncSession,
        *,
        content_id: str,
        content_type: str,
        user_id: str,
    ) -> bool:
        """Release lock if held by the user."""
        lock = await self._get_lock(db, content_id, content_type)
        if lock is None or lock.user_id != user_id:
            return False
        await db.delete(lock)
        await db.flush()
        return True

    async def get_active_lock(
        self,
        db: AsyncSession,
        content_id: str,
        content_type: str,
    ) -> ContentLockModel | None:
        """Return active lock if any."""
        await self._expire_stale_locks(db)
        lock = await self._get_lock(db, content_id, content_type)
        if lock is None:
            return None
        if lock.expires_at <= datetime.now(UTC):
            await db.delete(lock)
            await db.flush()
            return None
        return lock

    async def _get_lock(
        self,
        db: AsyncSession,
        content_id: str,
        content_type: str,
    ) -> ContentLockModel | None:
        result = await db.execute(
            select(ContentLockModel).where(
                ContentLockModel.content_id == content_id,
                ContentLockModel.content_type == content_type,
            )
        )
        return result.scalar_one_or_none()

    async def _expire_stale_locks(self, db: AsyncSession) -> None:
        now = datetime.now(UTC)
        result = await db.execute(
            select(ContentLockModel).where(ContentLockModel.expires_at <= now)
        )
        for lock in result.scalars().all():
            await db.delete(lock)
        await db.flush()


__all__ = ["OptimisticLockService"]
