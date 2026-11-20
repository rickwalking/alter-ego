"""ffprobe, ffmpeg, downloads and cover JPEGs for reposts (ADR-0031).

Every process runs with an argument list (never a shell) and a deadline.
Files live under ``output/reposts/{id}/``, the volume the web and worker
containers share.
"""

from __future__ import annotations

import asyncio
import contextlib
import shutil
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import UUID

import httpx
import structlog

from rag_backend.domain.constants import ENCODING_UTF8
from rag_backend.modules.autopilot.domain.repost_render import (
    RenderPlan,
    ffmpeg_args,
    ffprobe_args,
    ffprobe_file_args,
    parse_duration,
)
from rag_backend.modules.autopilot.reels_constants import (
    FFMPEG_BINARY,
    FFPROBE_BINARY,
    LOG_PROBE_FAILED,
    LOG_REELS,
)
from rag_backend.modules.autopilot.repost_constants import (
    DOWNLOAD_CHUNK_BYTES,
    DOWNLOAD_MAX_BYTES,
    DOWNLOAD_TIMEOUT_SECONDS,
    ERR_RENDER_FAILED,
    ERR_RENDER_TOO_LARGE,
    ERR_RENDER_UNAVAILABLE,
    ERR_SOURCE_UNAVAILABLE,
    PROBE_TIMEOUT_SECONDS,
    RENDER_HEIGHT,
    RENDER_MAX_BYTES,
    RENDER_TIMEOUT_SECONDS,
    RENDER_WIDTH,
    REPOSTS_DIR_NAME,
)

logger = structlog.get_logger()

_HTTPS = "https://"
_JPEG = "JPEG"
_JPEG_QUALITY = 90
_RGB = "RGB"


class RenderError(Exception):
    """A render step failed; ``code`` is the stored error code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, kw_only=True)
class _Run:
    args: list[str]
    timeout: float


def reposts_dir(carousel_output_dir: str) -> Path:
    """``output/reposts`` next to the carousel output directory."""
    return Path(carousel_output_dir).resolve().parent / REPOSTS_DIR_NAME


def repost_dir(root: Path, repost_id: UUID) -> Path:
    """The files of one repost."""
    return root / str(repost_id)


class FfprobeReelProbe:
    """``ReelProbe`` over ffprobe. None when ffprobe is missing or fails."""

    def __init__(self, timeout: float = PROBE_TIMEOUT_SECONDS) -> None:
        self._timeout = timeout

    async def duration(self, url: str) -> float | None:
        """Seconds of an https video."""
        if not url.startswith(_HTTPS) or shutil.which(FFPROBE_BINARY) is None:
            return None
        try:
            out = await _run(_Run(args=ffprobe_args(url), timeout=self._timeout))
        except RenderError:
            logger.info(LOG_REELS, outcome=LOG_PROBE_FAILED)
            return None
        return parse_duration(out)


class FfmpegRenderer:
    """Runs one render plan and checks the output size."""

    def __init__(self, max_bytes: int = RENDER_MAX_BYTES) -> None:
        self._max_bytes = max_bytes
        self._timeout = PROBE_TIMEOUT_SECONDS

    async def render(self, plan: RenderPlan) -> int:
        """The output size in bytes; raises ``RenderError``."""
        if shutil.which(FFMPEG_BINARY) is None:
            raise RenderError(ERR_RENDER_UNAVAILABLE)
        await _run(_Run(args=ffmpeg_args(plan), timeout=RENDER_TIMEOUT_SECONDS))
        output = Path(plan.output)
        if not output.is_file():
            raise RenderError(ERR_RENDER_FAILED)
        size = output.stat().st_size
        if size >= self._max_bytes:
            output.unlink(missing_ok=True)
            raise RenderError(ERR_RENDER_TOO_LARGE)
        return size

    async def duration(self, path: str) -> float | None:
        """Seconds of a local file (the rendered preview)."""
        args = ffprobe_file_args(path)
        try:
            out = await _run(_Run(args=args, timeout=self._timeout))
        except RenderError:
            return None
        return parse_duration(out)


class HttpDownloader:
    """Streams an https URL into a file, bounded in size and time."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def download(self, url: str, target: Path) -> None:
        """Write the body to ``target``; raises ``RenderError``."""
        if not url.startswith(_HTTPS):
            raise RenderError(ERR_SOURCE_UNAVAILABLE)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            async with asyncio.timeout(DOWNLOAD_TIMEOUT_SECONDS):
                await self._stream(url, target)
        except (httpx.HTTPError, TimeoutError, OSError):
            target.unlink(missing_ok=True)
            raise RenderError(ERR_SOURCE_UNAVAILABLE) from None

    async def _stream(self, url: str, target: Path) -> None:
        written = 0
        async with self._client.stream("GET", url, follow_redirects=True) as response:
            response.raise_for_status()
            with target.open("wb") as handle:
                async for chunk in response.aiter_bytes(DOWNLOAD_CHUNK_BYTES):
                    written += len(chunk)
                    if written > DOWNLOAD_MAX_BYTES:
                        raise OSError(ERR_SOURCE_UNAVAILABLE)
                    handle.write(chunk)


def write_jpeg(source: Path, target: Path) -> None:
    """Re-encode an image as a 1080x1920 RGB JPEG (padded, never stretched)."""
    from PIL import Image, ImageOps

    with Image.open(source) as image:
        fitted = ImageOps.pad(image.convert(_RGB), (RENDER_WIDTH, RENDER_HEIGHT))
    buffer = BytesIO()
    fitted.save(buffer, format=_JPEG, quality=_JPEG_QUALITY)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(buffer.getvalue())


def write_text(target: Path, text: str) -> None:
    """Write a UTF-8 text file (the hook for drawtext)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding=ENCODING_UTF8)


async def _run(run: _Run) -> str:
    try:
        process = await asyncio.create_subprocess_exec(
            *run.args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError:
        raise RenderError(ERR_RENDER_UNAVAILABLE) from None
    try:
        async with asyncio.timeout(run.timeout):
            stdout, _stderr = await process.communicate()
    except TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            process.kill()
        raise RenderError(ERR_RENDER_FAILED) from None
    if process.returncode != 0:
        raise RenderError(ERR_RENDER_FAILED)
    return stdout.decode(ENCODING_UTF8, errors="replace")


__all__ = [
    "FfmpegRenderer",
    "FfprobeReelProbe",
    "HttpDownloader",
    "RenderError",
    "repost_dir",
    "reposts_dir",
    "write_jpeg",
    "write_text",
]
