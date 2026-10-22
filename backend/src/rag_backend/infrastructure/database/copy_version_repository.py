"""PostgreSQL store of the caption / LinkedIn version history (``content_versions``)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Row, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.domain.constants.carousel_copy_versions import (
    CONTENT_TYPE_CAROUSEL_COPY,
    SNAPSHOT_FIELD_KEY,
    SNAPSHOT_RESTORED_FROM_KEY,
    SNAPSHOT_TEXT_KEY,
)
from rag_backend.domain.models.carousel_copy_version import (
    CopyVersion,
    NewCopyVersion,
)
from rag_backend.infrastructure.database.models.source_comment import (
    ContentVersionModel,
)
from rag_backend.infrastructure.database.models.user import UserModel

ERR_CREATED_AT_TYPE = "content_versions.created_at is not a datetime"


def _snapshot(version: NewCopyVersion) -> dict[str, str | int]:
    snapshot: dict[str, str | int] = {
        SNAPSHOT_FIELD_KEY: version.field,
        SNAPSHOT_TEXT_KEY: version.text,
    }
    if version.restored_from is not None:
        snapshot[SNAPSHOT_RESTORED_FROM_KEY] = version.restored_from
    return snapshot


def _restored_from(snapshot: dict[str, object]) -> int | None:
    value = snapshot.get(SNAPSHOT_RESTORED_FROM_KEY)
    return value if isinstance(value, int) else None


def _optional_text(value: object) -> str | None:
    return None if value is None else str(value)


def _to_version(row: Row[tuple[object, ...]]) -> CopyVersion:
    """One selected ``(number, snapshot, author_id, created_at, name)`` row."""
    number, raw_snapshot, author_id, created_at, author_name = row
    snapshot: dict[str, object] = (
        dict(raw_snapshot) if isinstance(raw_snapshot, dict) else {}
    )
    if not isinstance(created_at, datetime):
        raise TypeError(ERR_CREATED_AT_TYPE)
    return CopyVersion(
        version_number=int(str(number)),
        field=str(snapshot.get(SNAPSHOT_FIELD_KEY, "")),
        text=str(snapshot.get(SNAPSHOT_TEXT_KEY, "")),
        author_id=_optional_text(author_id),
        author_name=_optional_text(author_name),
        created_at=created_at,
        restored_from=_restored_from(snapshot),
    )


class PostgresCopyVersionStore:
    """``content_versions`` rows of type ``carousel_copy``, numbered per carousel."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_versions(self, project_id: str) -> list[CopyVersion]:
        """The carousel's versions, newest first, with the author's name."""
        stmt = (
            select(
                ContentVersionModel.version_number,
                ContentVersionModel.snapshot,
                ContentVersionModel.author_id,
                ContentVersionModel.created_at,
                UserModel.full_name,
            )
            .outerjoin(UserModel, UserModel.id == ContentVersionModel.author_id)
            .where(
                ContentVersionModel.content_id == project_id,
                ContentVersionModel.content_type == CONTENT_TYPE_CAROUSEL_COPY,
            )
            .order_by(ContentVersionModel.version_number.desc())
        )
        rows = (await self._session.execute(stmt)).all()
        return [_to_version(row) for row in rows]

    async def add(self, project_id: str, versions: list[NewCopyVersion]) -> None:
        """Stage the versions after the carousel's highest number (no commit)."""
        if not versions:
            return
        latest = await self._session.scalar(
            select(func.max(ContentVersionModel.version_number)).where(
                ContentVersionModel.content_id == project_id,
                ContentVersionModel.content_type == CONTENT_TYPE_CAROUSEL_COPY,
            )
        )
        number = int(latest or 0)
        for version in versions:
            number += 1
            self._session.add(
                ContentVersionModel(
                    id=str(uuid.uuid4()),
                    content_id=project_id,
                    content_type=CONTENT_TYPE_CAROUSEL_COPY,
                    version_number=number,
                    snapshot=_snapshot(version),
                    change_summary=version.summary,
                    author_id=version.author_id,
                )
            )
        await self._session.flush()


__all__ = ["PostgresCopyVersionStore"]
