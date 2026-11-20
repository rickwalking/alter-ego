"""Keyless ``/r/{repost_id}/{file}``: the preview and covers Graph and Telegram fetch.

Only the three known file names are served, only for a repost id that exists
and is not rejected or expired, and only from that repost's own directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.api.dependencies.database import get_db
from rag_backend.infrastructure.config.settings import Settings, get_settings
from rag_backend.modules.autopilot.bootstrap_repost import repost_files_root
from rag_backend.modules.autopilot.infrastructure.repost_store import SqlRepostStore
from rag_backend.modules.autopilot.infrastructure.repost_video import repost_dir
from rag_backend.modules.autopilot.repost_constants import (
    PATH_PUBLIC_FILE,
    PATH_PUBLIC_PREFIX,
    PUBLIC_FILES,
    SERVED_STATUSES,
    TAG_REPOST_FILES,
)

router = APIRouter(prefix=PATH_PUBLIC_PREFIX, tags=[TAG_REPOST_FILES])


@dataclass(frozen=True, kw_only=True)
class RepostFiles:
    """The repost store and the files directory."""

    store: SqlRepostStore
    root: Path


def repost_files(
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RepostFiles:
    """Where repost files live, and the rows that say whether to serve them."""
    return RepostFiles(store=SqlRepostStore(session), root=repost_files_root(settings))


@router.head(PATH_PUBLIC_FILE, include_in_schema=False)
@router.get(PATH_PUBLIC_FILE)
async def get_repost_file(
    repost_id: UUID,
    file_name: str,
    files: Annotated[RepostFiles, Depends(repost_files)],
) -> FileResponse:
    """The file, or 404. HEAD is answered too, for fetchers that probe first."""
    media_type = PUBLIC_FILES.get(file_name)
    repost = await files.store.get(repost_id)
    if media_type is None or repost is None or repost.status not in SERVED_STATUSES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    path = repost_dir(files.root, repost_id) / file_name
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return FileResponse(path, media_type=media_type)


__all__ = ["RepostFiles", "repost_files", "router"]
