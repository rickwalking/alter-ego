"""Drop the page cache of carousel files this process wrote and will not read again.

Linux charges the page cache of a write to the cgroup of the writer. A carousel run
writes its slide JPGs, HD slides, PDFs and artifact copies (about 120 to 220 MB),
which the backend serves later; left cached, those pages count against the
generation worker's memory cap run after run. ``release_page_cache`` flushes each
file (dirty pages cannot be dropped) and then advises the kernel to drop its cached
pages. The content stays on disk; a later read just goes to disk. Symlinks are not
followed, failures are skipped file by file, and platforms without
``posix_fadvise`` release nothing.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

LOG_PAGE_CACHE_RELEASE_FAILED = "page_cache_release_failed"

_SUPPORTED = hasattr(os, "posix_fadvise")
_WHOLE_FILE_OFFSET = 0
_WHOLE_FILE_LENGTH = 0


def release_page_cache(root: Path) -> int:
    """Flush and drop the cached pages of ``root`` (a file, or every file under it).

    Returns the number of files released.
    """
    if not _SUPPORTED:
        return 0
    return sum(1 for path in _regular_files(root) if _release_file(path))


def _regular_files(root: Path) -> Iterator[Path]:
    if root.is_symlink():
        return
    if root.is_file():
        yield root
        return
    if not root.is_dir():
        return
    for directory, _subdirs, names in os.walk(root):
        for name in names:
            path = Path(directory) / name
            if path.is_file() and not path.is_symlink():
                yield path


def _release_file(path: Path) -> bool:
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError:
        logger.debug(LOG_PAGE_CACHE_RELEASE_FAILED, path=str(path))
        return False
    try:
        os.fdatasync(fd)
        os.posix_fadvise(
            fd, _WHOLE_FILE_OFFSET, _WHOLE_FILE_LENGTH, os.POSIX_FADV_DONTNEED
        )
    except OSError:
        logger.debug(LOG_PAGE_CACHE_RELEASE_FAILED, path=str(path))
        return False
    finally:
        os.close(fd)
    return True


__all__ = ["release_page_cache"]
