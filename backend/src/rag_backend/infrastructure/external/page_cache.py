"""Drop the page cache of carousel files this process wrote and will not read again.

Linux charges the page cache of a write to the cgroup of the writer. A carousel run
writes its slide JPGs, HD slides, PDFs and artifact copies (about 120 to 220 MB),
which the backend serves later; left cached, those pages count against the
generation worker's memory cap run after run. ``release_page_cache`` flushes each
file (dirty pages cannot be dropped) and then advises the kernel to drop its cached
pages. The content stays on disk; a later read just goes to disk. Symlinks are not
followed, and platforms without ``posix_fadvise`` release nothing. Releasing is an
optimisation, so it never raises: a file or folder that cannot be read is skipped, and
any other filesystem error stops the release with what was done so far.
"""

from __future__ import annotations

import os
import stat
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
    released = 0
    try:
        for path in _regular_files(root):
            released += int(_release_file(path))
    except OSError:
        logger.debug(LOG_PAGE_CACHE_RELEASE_FAILED, path=str(root))
    return released


def _is_regular_file(path: Path) -> bool:
    """True for a regular file; a symlink (even to a file) is not followed.

    A path that vanished or cannot be inspected is not a file to release.
    """
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def _regular_files(root: Path) -> Iterator[Path]:
    if not root.exists() or root.is_symlink():
        return
    if _is_regular_file(root):
        yield root
        return
    for directory, _subdirs, names in os.walk(root):
        for name in names:
            path = Path(directory) / name
            if _is_regular_file(path):
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
