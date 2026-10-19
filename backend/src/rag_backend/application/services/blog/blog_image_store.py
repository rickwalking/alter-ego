"""The blog-images store (AE-0424; shared with AE-0425's bulk generation).

Files live at ``<carousel_output_dir>/blog-images/<post_id>/<uuid4>.<ext>``.
The provider writes into a temporary ``.part`` name; :meth:`BlogImageStore.
finalize` sniffs the real format (PNG / JPEG / WebP: gpt-image-2 returns PNG
by default) and renames the file to the matching extension, so the served
``Content-Type`` is always right. Only files referenced by the current content
or a version snapshot are kept (:meth:`prune`), so regenerate / remove /
restore / a failed write leave no orphan while history stays restorable.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from rag_backend.application.services.asset_cdn_service import AssetCdnService
from rag_backend.domain.constants.blog_editor import (
    BLOG_IMAGE_PARTIAL_SUFFIX,
    BLOG_IMAGE_TYPES,
    BLOG_IMAGES_DIR_NAME,
    BLOG_IMAGES_ROUTE_PREFIX,
)

KEY_URL = "url"
MAGIC_PREFIX_BYTES = 12


def image_extension(head: bytes) -> str | None:
    """The file extension of PNG / JPEG / WebP bytes, else ``None``."""
    for extension, (offset, magic) in BLOG_IMAGE_TYPES.items():
        if head[offset : offset + len(magic)] == magic:
            return extension
    return None


def _urls(value: object) -> Iterable[str]:
    if isinstance(value, dict):
        url = value.get(KEY_URL)
        if isinstance(url, str):
            yield url
        for child in value.values():
            yield from _urls(child)
    elif isinstance(value, list):
        for child in value:
            yield from _urls(child)


def referenced_filenames(*documents: object) -> set[str]:
    """Basenames of every image URL in the given documents / history lists."""
    return {url.rsplit("/", 1)[-1] for doc in documents for url in _urls(doc)}


@dataclass(frozen=True)
class BlogImageStore:
    """Where blog image bytes live and how they are addressed."""

    root: Path
    cdn: AssetCdnService

    def new_path(self, post_id: str) -> Path:
        """A fresh temporary ``<root>/<post_id>/<uuid>.part`` path."""
        directory = self.root / post_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{uuid.uuid4()}{BLOG_IMAGE_PARTIAL_SUFFIX}"

    @staticmethod
    def finalize(path: Path) -> Path | None:
        """Rename a written ``.part`` file to its real type; ``None`` if invalid."""
        if not path.is_file() or path.stat().st_size == 0:
            path.unlink(missing_ok=True)
            return None
        with path.open("rb") as handle:
            extension = image_extension(handle.read(MAGIC_PREFIX_BYTES))
        if extension is None:
            path.unlink(missing_ok=True)
            return None
        return path.rename(path.with_suffix(f".{extension}"))

    def url_for(self, post_id: str, filename: str) -> str:
        """The canonical URL: CDN when enabled, else the same-origin route."""
        if self.cdn.enabled:
            return self.cdn.resolve_url(f"{BLOG_IMAGES_DIR_NAME}/{post_id}/{filename}")
        return f"{BLOG_IMAGES_ROUTE_PREFIX}/{post_id}/{filename}"

    def file_for(self, post_id: str, filename: str) -> Path | None:
        """The stored file, or ``None`` when it does not exist."""
        path = self.root / post_id / filename
        return path if path.is_file() else None

    def delete(self, post_id: str, filename: str) -> None:
        """Remove one stored file (no error when it is already gone)."""
        (self.root / post_id / filename).unlink(missing_ok=True)

    def prune(self, post_id: str, keep: set[str]) -> int:
        """Delete this post's files not in ``keep``; returns how many."""
        directory = self.root / post_id
        if not directory.is_dir():
            return 0
        stale = [p for p in directory.iterdir() if p.is_file() and p.name not in keep]
        for path in stale:
            path.unlink(missing_ok=True)
        return len(stale)


__all__ = ["BlogImageStore", "image_extension", "referenced_filenames"]
