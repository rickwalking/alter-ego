"""Turn a repost draft into files: preview.mp4, cover.jpg, original_cover.jpg.

The source video is the owner's upload when the draft has one, else it is
downloaded fresh (its CDN URL expires). It is rendered once and deleted. The
preview is the exact file Graph will fetch, so the owner approves what gets
published.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID

from rag_backend.modules.autopilot.application.repost_tick_ports import (
    RenderedFiles,
    RepostRenderError,
    StudioJob,
)
from rag_backend.modules.autopilot.domain.repost import Repost
from rag_backend.modules.autopilot.domain.repost_render import (
    HookOverlay,
    RenderPlan,
    wrap_hook,
)
from rag_backend.modules.autopilot.infrastructure.repost_notifier import fits_telegram
from rag_backend.modules.autopilot.infrastructure.repost_video import (
    FfmpegRenderer,
    HttpDownloader,
    RenderError,
    repost_dir,
    write_jpeg,
    write_text,
)
from rag_backend.modules.autopilot.repost_constants import (
    ERR_RENDER_DURATION,
    ERR_SOURCE_UNAVAILABLE,
    FILE_COVER,
    FILE_ORIGINAL_COVER,
    FILE_PREVIEW,
    FILE_SOURCE,
    FINAL_MAX_SECONDS,
    FINAL_MIN_SECONDS,
    HOOK_FONT_FILE,
    HOOK_LINE_FILE,
    PUBLIC_URL_TEMPLATE,
)

_DURATION_SLACK_SECONDS = 0.5
_ORIGINAL_DOWNLOAD = "original_cover.src"


class SourceFiles(Protocol):
    """Where a draft's uploaded source video is stored."""

    async def for_repost(self, repost_id: UUID) -> Path | None:
        """The upload's path when the draft has one (it may be gone)."""
        ...


class CoverFiles(Protocol):
    """Where a Reel cover asset's image is stored."""

    async def path(self, asset_id: UUID) -> Path | None:
        """The stored image, or None when it is gone."""
        ...


@dataclass(frozen=True, kw_only=True)
class StudioConfig:
    """The reposts directory, the public origin and the collaborators."""

    root: Path
    public_base_url: str
    downloader: HttpDownloader
    renderer: FfmpegRenderer
    covers: CoverFiles
    font_file: str = HOOK_FONT_FILE
    sources: SourceFiles | None = None


class FileRepostStudio:
    """``RepostStudio`` on the shared output volume."""

    def __init__(self, config: StudioConfig) -> None:
        self._config = config

    async def prepare(self, job: StudioJob) -> RenderedFiles:
        """Render the preview and write both covers."""
        folder = repost_dir(self._config.root, job.repost.id)
        upload = await self._upload(job.repost)
        try:
            source = await self._source(job, folder, upload)
            preview, size = await self._preview(job, folder, source)
        except RenderError as exc:
            raise RepostRenderError(exc.code) from None
        finally:
            (folder / FILE_SOURCE).unlink(missing_ok=True)
            if upload is not None:
                upload.unlink(missing_ok=True)
        return RenderedFiles(
            preview=preview,
            cover=await self._cover(job.repost, folder),
            original_cover=await self._original(job, folder),
            fits_telegram=fits_telegram(preview),
            source_size=size,
        )

    def public_url(self, repost: Repost, file_name: str) -> str:
        """``{origin}/r/{id}/{file}``."""
        return PUBLIC_URL_TEMPLATE.format(
            base=self._config.public_base_url.rstrip("/"),
            repost_id=repost.id,
            file_name=file_name,
        )

    def existing(self, repost: Repost, file_name: str) -> Path | None:
        """The file when it exists."""
        path = repost_dir(self._config.root, repost.id) / file_name
        return path if path.is_file() else None

    async def _upload(self, repost: Repost) -> Path | None:
        sources = self._config.sources
        return None if sources is None else await sources.for_repost(repost.id)

    async def _source(self, job: StudioJob, folder: Path, upload: Path | None) -> Path:
        """The owner's upload when the draft has one, else the Graph video."""
        if upload is not None:
            if not upload.is_file():
                raise RenderError(ERR_SOURCE_UNAVAILABLE)
            return upload
        if not job.reel.video_url:
            raise RenderError(ERR_SOURCE_UNAVAILABLE)
        source = folder / FILE_SOURCE
        await self._config.downloader.download(job.reel.video_url, source)
        return source

    async def _preview(
        self, job: StudioJob, folder: Path, source: Path
    ) -> tuple[Path, tuple[int, int] | None]:
        size = await self._config.renderer.size(str(source))
        output = folder / FILE_PREVIEW
        plan = RenderPlan(
            source=str(source),
            output=str(output),
            trim_start_s=job.repost.trim_start_s,
            trim_end_s=job.repost.trim_end_s,
            hook=self._hook(job.repost, folder),
        )
        await self._config.renderer.render(plan)
        await self._check_length(output)
        return output, size

    def _hook(self, repost: Repost, folder: Path) -> HookOverlay | None:
        if not repost.hook_text:
            return None
        files: list[str] = []
        for index, line in enumerate(wrap_hook(repost.hook_text)):
            path = folder / HOOK_LINE_FILE.format(index=index)
            write_text(path, line)
            files.append(str(path))
        return HookOverlay(
            line_files=tuple(files),
            duration_s=repost.hook_duration_s,
            font_file=self._config.font_file,
        )

    async def _check_length(self, output: Path) -> None:
        seconds = await self._config.renderer.duration(str(output))
        low = FINAL_MIN_SECONDS - _DURATION_SLACK_SECONDS
        high = FINAL_MAX_SECONDS + _DURATION_SLACK_SECONDS
        if seconds is None or not low <= seconds <= high:
            output.unlink(missing_ok=True)
            raise RenderError(ERR_RENDER_DURATION)

    async def _cover(self, repost: Repost, folder: Path) -> Path | None:
        if repost.cover_asset_id is None:
            return None
        source = await self._config.covers.path(repost.cover_asset_id)
        if source is None:
            return None
        target = folder / FILE_COVER
        write_jpeg(source, target)
        return target

    async def _original(self, job: StudioJob, folder: Path) -> Path | None:
        if not job.reel.thumbnail_url:
            return None
        raw = folder / _ORIGINAL_DOWNLOAD
        target = folder / FILE_ORIGINAL_COVER
        try:
            await self._config.downloader.download(job.reel.thumbnail_url, raw)
            write_jpeg(raw, target)
        except (RenderError, OSError, ValueError):
            return None
        finally:
            with contextlib.suppress(OSError):
                raw.unlink(missing_ok=True)
        return target


__all__ = ["CoverFiles", "FileRepostStudio", "StudioConfig"]
