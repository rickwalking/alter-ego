"""PostgreSQL store of the caption / LinkedIn version history (``content_versions``)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
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


def _to_version(model: ContentVersionModel, author_name: str | None) -> CopyVersion:
    snapshot: dict[str, object] = dict(model.snapshot or {})
    return CopyVersion(
        version_number=int(model.version_number),
        field=str(snapshot.get(SNAPSHOT_FIELD_KEY, "")),
        text=str(snapshot.get(SNAPSHOT_TEXT_KEY, "")),
        author_id=model.author_id,
        author_name=author_name,
        created_at=model.created_at,
        restored_from=_restored_from(snapshot),
    )


class PostgresCopyVersionStore:
    """``content_versions`` rows of type ``carousel_copy``, numbered per carousel."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_versions(self, project_id: str) -> list[CopyVersion]:
        """The carousel's versions, newest first, with the author's name."""
        stmt = (
            select(ContentVersionModel, UserModel.full_name)
            .outerjoin(UserModel, UserModel.id == ContentVersionModel.author_id)
            .where(
                ContentVersionModel.content_id == project_id,
                ContentVersionModel.content_type == CONTENT_TYPE_CAROUSEL_COPY,
            )
            .order_by(ContentVersionModel.version_number.desc())
        )
        rows = (await self._session.execute(stmt)).all()
        return [_to_version(model, name) for model, name in rows]

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
