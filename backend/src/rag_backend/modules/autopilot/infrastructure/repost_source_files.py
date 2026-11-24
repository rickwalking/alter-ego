"""Where uploaded source videos live, how they are written and probed.

Uploads sit in ``output/reposts/sources/`` on the volume the web and worker
containers share. ffprobe runs with an argument list and a deadline.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import shutil
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID

from rag_backend.domain.constants import ENCODING_UTF8
from rag_backend.modules.autopilot.domain.repost_source import (
    RepostSource,
    SourceError,
    VideoProbe,
)
from rag_backend.modules.autopilot.reels_constants import FFPROBE_BINARY
from rag_backend.modules.autopilot.repost_source_constants import (
    ERR_SOURCE_TOO_LARGE,
    FFPROBE_JSON,
    FFPROBE_STREAM_ENTRIES,
    PROBE_KEY_CODEC,
    PROBE_KEY_DURATION,
    PROBE_KEY_FORMAT,
    PROBE_KEY_HEIGHT,
    PROBE_KEY_STREAMS,
    PROBE_KEY_WIDTH,
    SOURCE_FILE_TEMPLATE,
    SOURCE_MAX_BYTES,
    SOURCE_PART_SUFFIX,
    SOURCE_PROBE_TIMEOUT_SECONDS,
    SOURCES_DIR_NAME,
)

_PROTOCOLS_FILE = "file"


def sources_dir(root: Path) -> Path:
    """``output/reposts/sources``."""
    return root / SOURCES_DIR_NAME


def source_file_name(asset_id: UUID) -> str:
    """``{asset_id}.mp4``."""
    return SOURCE_FILE_TEMPLATE.format(asset_id=asset_id)


def source_path(root: Path, source: RepostSource) -> Path:
    """The stored file of an upload."""
    return sources_dir(root) / source.file_name


def part_path(root: Path, asset_id: UUID) -> Path:
    """The file an upload is streamed into before it is checked."""
    return sources_dir(root) / (source_file_name(asset_id) + SOURCE_PART_SUFFIX)


async def write_chunks(
    chunks: AsyncIterator[bytes], target: Path, max_bytes: int = SOURCE_MAX_BYTES
) -> int:
    """Stream ``chunks`` into ``target``; ``source_too_large`` past the cap."""
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        return await _write(chunks, target, max_bytes)
    except BaseException:
        target.unlink(missing_ok=True)
        raise


async def _write(chunks: AsyncIterator[bytes], target: Path, max_bytes: int) -> int:
    written = 0
    with target.open("wb") as handle:
        async for chunk in chunks:
            written += len(chunk)
            _check_cap(written, max_bytes)
            handle.write(chunk)
    return written


def _check_cap(written: int, max_bytes: int) -> None:
    if written > max_bytes:
        raise SourceError(ERR_SOURCE_TOO_LARGE)


def ffprobe_video_args(path: str) -> list[str]:
    """Read codec, size and duration of a local file as JSON."""
    return [
        FFPROBE_BINARY,
        "-v",
        "error",
        "-protocol_whitelist",
        _PROTOCOLS_FILE,
        "-select_streams",
        "v:0",
        "-show_entries",
        FFPROBE_STREAM_ENTRIES,
        "-of",
        FFPROBE_JSON,
        path,
    ]


def parse_video_probe(output: str) -> VideoProbe | None:
    """The first video stream of ffprobe's JSON, or None when there is none."""
    try:
        data = json.loads(output)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    streams = data.get(PROBE_KEY_STREAMS)
    fmt = data.get(PROBE_KEY_FORMAT)
    if not isinstance(streams, list) or not streams or not isinstance(fmt, dict):
        return None
    return _stream_probe(streams[0], _seconds(fmt.get(PROBE_KEY_DURATION)))


def _stream_probe(
    stream: dict[str, str | int] | str, duration: float | None
) -> VideoProbe | None:
    if not isinstance(stream, dict) or duration is None:
        return None
    codec = stream.get(PROBE_KEY_CODEC)
    width = stream.get(PROBE_KEY_WIDTH)
    height = stream.get(PROBE_KEY_HEIGHT)
    if not isinstance(codec, str):
        return None
    if not isinstance(width, int) or not isinstance(height, int):
        return None
    return VideoProbe(codec=codec, width=width, height=height, duration_s=duration)


def _seconds(value: str | float | None) -> float | None:
    if not isinstance(value, str | int | float) or isinstance(value, bool):
        return None
    try:
        seconds = float(value)
    except ValueError:
        return None
    return seconds if seconds > 0 else None


class FfprobeVideoProbe:
    """``VideoProber`` over ffprobe. None when ffprobe is missing or fails."""

    def __init__(self, timeout: float = SOURCE_PROBE_TIMEOUT_SECONDS) -> None:
        self._timeout = timeout

    async def probe(self, path: Path) -> VideoProbe | None:
        """Codec, size and duration of a local video."""
        if shutil.which(FFPROBE_BINARY) is None:
            return None
        try:
            process = await asyncio.create_subprocess_exec(
                *ffprobe_video_args(str(path)),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError:
            return None
        try:
            async with asyncio.timeout(self._timeout):
                stdout, _stderr = await process.communicate()
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                process.kill()
            return None
        if process.returncode != 0:
            return None
        return parse_video_probe(stdout.decode(ENCODING_UTF8, errors="replace"))


class FileSourceFolder:
    """``SourceFolder`` under ``output/reposts/sources``."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def promote(self, part: Path, asset_id: UUID) -> str:
        """Rename ``{id}.mp4.part`` to ``{id}.mp4``."""
        name = source_file_name(asset_id)
        part.replace(sources_dir(self._root) / name)
        return name

    def remove(self, source: RepostSource) -> None:
        """Delete the file; a missing one is fine."""
        source_path(self._root, source).unlink(missing_ok=True)


__all__ = [
    "FfprobeVideoProbe",
    "FileSourceFolder",
    "ffprobe_video_args",
    "parse_video_probe",
    "part_path",
    "source_file_name",
    "source_path",
    "sources_dir",
    "write_chunks",
]
