"""Unit tests for releasing the page cache of written carousel files.

Feature: tests/features/worker_page_cache_ae0555.feature
"""

from __future__ import annotations

import ctypes
import mmap
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from rag_backend.infrastructure.external import page_cache
from rag_backend.infrastructure.external.page_cache import release_page_cache

_MODULE_OS = "rag_backend.infrastructure.external.page_cache.os"


def _write(path: Path, data: bytes = b"slide") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


class _Spy:
    """Records which inodes were synced and advised, by path."""

    def __init__(self) -> None:
        self.synced: list[str] = []
        self.advised: list[tuple[str, int, int, int]] = []
        self._paths: dict[int, str] = {}

    def track(self, fd: int, path: str) -> None:
        self._paths[fd] = path

    def fdatasync(self, fd: int) -> None:
        self.synced.append(self._paths[fd])

    def posix_fadvise(self, fd: int, offset: int, length: int, advice: int) -> None:
        self.advised.append((self._paths[fd], offset, length, advice))


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> _Spy:
    recorder = _Spy()
    real_open = os.open

    def tracking_open(path: str, flags: int) -> int:
        fd = real_open(path, flags)
        recorder.track(fd, str(path))
        return fd

    monkeypatch.setattr(f"{_MODULE_OS}.open", tracking_open)
    monkeypatch.setattr(f"{_MODULE_OS}.fdatasync", recorder.fdatasync)
    monkeypatch.setattr(f"{_MODULE_OS}.posix_fadvise", recorder.posix_fadvise)
    return recorder


@pytest.mark.unit
class TestReleasePageCache:
    def test_releases_every_file_under_the_directory(
        self, tmp_path: Path, spy: _Spy
    ) -> None:
        """Scenario: Releasing a directory drops the cache of every file under it."""
        files = {
            str(_write(tmp_path / "pt" / "slide_1.jpg")),
            str(_write(tmp_path / "pt" / "hd" / "slide_1.jpg")),
            str(_write(tmp_path / "en" / "carousel.pdf")),
        }

        released = release_page_cache(tmp_path)

        assert released == len(files)
        assert set(spy.synced) == files
        assert {entry[0] for entry in spy.advised} == files
        assert {entry[1:] for entry in spy.advised} == {(0, 0, os.POSIX_FADV_DONTNEED)}

    def test_syncs_before_advising(self, tmp_path: Path, spy: _Spy) -> None:
        """Dirty pages are not dropped, so the data is flushed first."""
        order: list[str] = []
        sync = spy.fdatasync
        advise = spy.posix_fadvise

        def record_sync(fd: int) -> None:
            order.append("sync")
            sync(fd)

        def record_advise(fd: int, offset: int, length: int, advice: int) -> None:
            order.append("advise")
            advise(fd, offset, length, advice)

        _write(tmp_path / "slide_1.jpg")
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(f"{_MODULE_OS}.fdatasync", record_sync)
            patch.setattr(f"{_MODULE_OS}.posix_fadvise", record_advise)
            release_page_cache(tmp_path)

        assert order == ["sync", "advise"]

    def test_a_single_file_is_released(self, tmp_path: Path, spy: _Spy) -> None:
        target = _write(tmp_path / "carousel.pdf")
        _write(tmp_path / "other.jpg")

        assert release_page_cache(target) == 1
        assert spy.synced == [str(target)]

    def test_a_missing_path_releases_nothing(self, tmp_path: Path, spy: _Spy) -> None:
        assert release_page_cache(tmp_path / "missing") == 0
        assert spy.advised == []

    def test_symlinks_are_not_followed(self, tmp_path: Path, spy: _Spy) -> None:
        outside = _write(tmp_path / "outside" / "photo.jpg")
        output = tmp_path / "output"
        _write(output / "slide_1.jpg")
        (output / "link.jpg").symlink_to(outside)

        assert release_page_cache(output) == 1
        assert spy.synced == [str(output / "slide_1.jpg")]

    def test_one_failing_file_does_not_stop_the_others(
        self, tmp_path: Path, spy: _Spy, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: A file that cannot be released does not stop the others."""
        broken = _write(tmp_path / "a" / "broken.jpg")
        healthy = _write(tmp_path / "b" / "slide_2.jpg")
        tracking_open = os.open

        def failing_open(path: str, flags: int) -> int:
            if str(path) == str(broken):
                raise PermissionError(path)
            return tracking_open(path, flags)

        monkeypatch.setattr(f"{_MODULE_OS}.open", failing_open)

        assert release_page_cache(tmp_path) == 1
        assert spy.synced == [str(healthy)]

    def test_a_failing_advise_counts_the_file_as_not_released(
        self, tmp_path: Path, spy: _Spy, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write(tmp_path / "slide_1.jpg")

        def failing_advise(fd: int, offset: int, length: int, advice: int) -> None:
            raise OSError(fd)

        monkeypatch.setattr(f"{_MODULE_OS}.posix_fadvise", failing_advise)

        assert release_page_cache(tmp_path) == 0

    def test_no_fadvise_platform_is_a_no_op(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Releasing is a no-op where the platform has no fadvise."""
        _write(tmp_path / "slide_1.jpg")
        monkeypatch.setattr(page_cache, "_SUPPORTED", False)
        monkeypatch.setattr(
            f"{_MODULE_OS}.open",
            lambda *_: pytest.fail("no file is opened without fadvise"),
        )

        assert release_page_cache(tmp_path) == 0

    def test_real_release_keeps_the_file_content(self, tmp_path: Path) -> None:
        target = _write(tmp_path / "slide_1.jpg", b"jpeg-bytes")

        assert release_page_cache(tmp_path) == 1
        assert target.read_bytes() == b"jpeg-bytes"

    def test_a_file_that_vanished_is_skipped(
        self, tmp_path: Path, spy: _Spy, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        kept = _write(tmp_path / "slide_1.jpg")

        def walk_with_a_ghost(root: Path) -> Iterator[tuple[str, list[str], list[str]]]:
            yield str(root), [], ["slide_1.jpg", "gone.jpg"]

        monkeypatch.setattr(f"{_MODULE_OS}.walk", walk_with_a_ghost)

        assert release_page_cache(tmp_path) == 1
        assert spy.synced == [str(kept)]

    def test_a_filesystem_error_mid_walk_never_raises(
        self, tmp_path: Path, spy: _Spy, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        first = _write(tmp_path / "slide_1.jpg")

        def failing_walk(root: Path) -> Iterator[tuple[str, list[str], list[str]]]:
            yield str(root), [], ["slide_1.jpg"]
            raise OSError(root)

        monkeypatch.setattr(f"{_MODULE_OS}.walk", failing_walk)

        assert release_page_cache(tmp_path) == 1
        assert spy.synced == [str(first)]


def _resident_pages(path: Path) -> int:
    """Pages of ``path`` in the page cache (``mincore``; the pages are not read)."""
    size = path.stat().st_size
    pages = (size + mmap.PAGESIZE - 1) // mmap.PAGESIZE
    vector = (ctypes.c_ubyte * pages)()
    libc = ctypes.CDLL(None, use_errno=True)
    with path.open("rb") as handle:
        mapping = mmap.mmap(handle.fileno(), size, access=mmap.ACCESS_COPY)
        anchor = ctypes.c_char.from_buffer(mapping)
        result = libc.mincore(
            ctypes.c_void_p(ctypes.addressof(anchor)), ctypes.c_size_t(size), vector
        )
        del anchor
        mapping.close()
    assert result == 0, os.strerror(ctypes.get_errno())
    return sum(byte & 1 for byte in vector)


@pytest.mark.unit
class TestKernelDropsThePages:
    def test_written_pages_leave_the_page_cache(self) -> None:
        """Scenario: Releasing a directory drops the cache of every file under it.

        Runs on a disk-backed folder next to this test: tmpfs pages are memory, not
        cache, and fadvise cannot drop them.
        """
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            target = _write(Path(folder) / "slide_1.jpg", os.urandom(1 << 20))

            assert _resident_pages(target) > 0
            assert release_page_cache(Path(folder)) == 1
            assert _resident_pages(target) == 0
            assert len(target.read_bytes()) == 1 << 20
