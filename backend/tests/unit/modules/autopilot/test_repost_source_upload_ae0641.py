"""The source video upload: checks, files, probe, sweep and the studio.

Gherkin: tests/features/autopilot_repost_source_video_ae0641.feature
"""

from __future__ import annotations

import asyncio
import shutil
from collections.abc import AsyncIterator
from dataclasses import dataclass, replace
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from PIL import Image

from rag_backend.modules.autopilot.application.repost_source_upload import (
    RepostSourceUploads,
    SourceUpload,
    SourceUploadDeps,
)
from rag_backend.modules.autopilot.application.repost_tick_ports import (
    RepostRenderError,
    StudioJob,
)
from rag_backend.modules.autopilot.domain.repost_render import RenderPlan
from rag_backend.modules.autopilot.domain.repost_source import (
    SourceError,
    VideoProbe,
    check_video,
    source_usable,
)
from rag_backend.modules.autopilot.infrastructure.repost_source_files import (
    FfprobeVideoProbe,
    FileSourceFolder,
    ffprobe_video_args,
    parse_video_probe,
    part_path,
    source_path,
    sources_dir,
    write_chunks,
)
from rag_backend.modules.autopilot.infrastructure.repost_studio import (
    FileRepostStudio,
    StudioConfig,
)
from rag_backend.modules.autopilot.infrastructure.repost_video import (
    FfmpegRenderer,
    HttpDownloader,
)
from tests.unit.modules.autopilot.repost_fakes import NOW, Clock, reel, stored
from tests.unit.modules.autopilot.repost_source_fakes import (
    HD,
    FakeProber,
    MemorySources,
    source,
)

_PROBE_JSON = (
    '{"streams": [{"codec_name": "h264", "width": 1080, "height": 1920}],'
    ' "format": {"duration": "86.020000"}}'
)


async def _chunks(*parts: bytes) -> AsyncIterator[bytes]:
    for part in parts:
        yield part


# Scenario Outline: An unusable upload is refused and not kept
@pytest.mark.parametrize(
    ("probe", "code"),
    [
        (None, "source_not_video"),
        (replace(HD, codec="hevc"), "source_codec_unsupported"),
        (replace(HD, width=1920, height=1080), "source_not_portrait"),
        (replace(HD, width=1080, height=1080), "source_not_portrait"),
        (replace(HD, width=480, height=854), "source_not_portrait"),
        (replace(HD, duration_s=2.9), "source_duration_invalid"),
        (replace(HD, duration_s=180.1), "source_duration_invalid"),
    ],
)
def test_check_video_refusals(probe: VideoProbe | None, code: str) -> None:
    with pytest.raises(SourceError) as error:
        check_video(probe)
    assert error.value.code == code


# Scenario: An H.264 portrait video is stored and gets an asset_id
@pytest.mark.parametrize(
    "probe",
    [
        HD,
        replace(HD, width=720, height=1280),
        replace(HD, duration_s=3.0),
        replace(HD, duration_s=180.0),
    ],
)
def test_check_video_accepts_the_edges(probe: VideoProbe) -> None:
    assert check_video(probe) == probe


# Scenario Outline: A bad source_asset_id is refused
def test_source_usable() -> None:
    assert source_usable(source(), NOW)
    assert source_usable(source(), NOW + timedelta(hours=23, minutes=59))
    assert not source_usable(source(), NOW + timedelta(hours=24))
    assert not source_usable(source(repost_id=uuid4()), NOW)
    assert not source_usable(None, NOW)


# Scenario: An H.264 portrait video is stored and gets an asset_id
def test_parse_video_probe_reads_ffprobe_json() -> None:
    assert parse_video_probe(_PROBE_JSON) == VideoProbe(
        codec="h264", width=1080, height=1920, duration_s=86.02
    )
    assert parse_video_probe(_PROBE_JSON.replace('"86.020000"', "12")) == replace(
        HD, duration_s=12.0
    )


# Scenario Outline: An unusable upload is refused and not kept
@pytest.mark.parametrize(
    "output",
    [
        "not json",
        "[]",
        '{"streams": [], "format": {"duration": "5"}}',
        '{"streams": [{"codec_name": "h264", "width": 1, "height": 2}]}',
        '{"streams": ["x"], "format": {"duration": "5"}}',
        '{"streams": [{"width": 1080, "height": 1920}], "format": {"duration": "5"}}',
        '{"streams": [{"codec_name": "h264", "width": "1080", "height": 1920}],'
        ' "format": {"duration": "5"}}',
        '{"streams": [{"codec_name": "h264", "width": 1080, "height": null}],'
        ' "format": {"duration": "5"}}',
        '{"streams": [{"codec_name": "h264", "width": 1080, "height": 1920}],'
        ' "format": {"duration": "N/A"}}',
        '{"streams": [{"codec_name": "h264", "width": 1080, "height": 1920}],'
        ' "format": {"duration": "0"}}',
        '{"streams": [{"codec_name": "h264", "width": 1080, "height": 1920}],'
        ' "format": {"duration": true}}',
    ],
)
def test_parse_video_probe_refuses_bad_output(output: str) -> None:
    assert parse_video_probe(output) is None


def test_ffprobe_args_read_only_local_files() -> None:
    args = ffprobe_video_args("/tmp/x.mp4")
    assert args[args.index("-protocol_whitelist") + 1] == "file"
    assert args[args.index("-select_streams") + 1] == "v:0"
    assert args[args.index("-of") + 1] == "json"
    assert args[-1] == "/tmp/x.mp4"


# Scenario Outline: An unusable upload is refused and not kept
async def test_write_chunks_caps_and_cleans_up(tmp_path: Path) -> None:
    target = part_path(tmp_path, uuid4())
    assert await write_chunks(_chunks(b"ab", b"cd"), target, max_bytes=4) == 4
    assert target.read_bytes() == b"abcd"
    with pytest.raises(SourceError) as error:
        await write_chunks(_chunks(b"ab", b"cde"), target, max_bytes=4)
    assert error.value.code == "source_too_large"
    assert not target.exists()


# Scenario: An H.264 portrait video is stored and gets an asset_id
def test_folder_promotes_and_removes(tmp_path: Path) -> None:
    asset_id = uuid4()
    part = part_path(tmp_path, asset_id)
    part.parent.mkdir(parents=True)
    part.write_bytes(b"v")
    folder = FileSourceFolder(tmp_path)
    name = folder.promote(part, asset_id)
    assert name == f"{asset_id}.mp4"
    stored_file = sources_dir(tmp_path) / name
    assert stored_file.read_bytes() == b"v" and not part.exists()
    folder.remove(source(id=asset_id, file_name=name))
    assert not stored_file.exists()
    folder.remove(source(id=asset_id, file_name=name))


def _uploads(
    tmp_path: Path, prober: FakeProber | None = None
) -> tuple[RepostSourceUploads, MemorySources]:
    store = MemorySources()
    uploads = RepostSourceUploads(
        SourceUploadDeps(
            store=store,
            prober=prober or FakeProber(),
            folder=FileSourceFolder(tmp_path),
            clock=Clock(),
        )
    )
    return uploads, store


def _part(tmp_path: Path) -> SourceUpload:
    asset_id = uuid4()
    part = part_path(tmp_path, asset_id)
    part.parent.mkdir(parents=True, exist_ok=True)
    part.write_bytes(b"video")
    return SourceUpload(asset_id=asset_id, part=part, size_bytes=5)


# Scenario: An H.264 portrait video is stored and gets an asset_id
async def test_accept_stores_the_checked_upload(tmp_path: Path) -> None:
    uploads, store = _uploads(tmp_path)
    upload = _part(tmp_path)
    kept = await uploads.accept(upload)
    assert kept.id == upload.asset_id and kept.probe == HD
    assert kept.size_bytes == 5 and kept.created_at == NOW
    assert kept.repost_id is None
    assert store.rows[kept.id] == kept and store.commits == 1
    assert source_path(tmp_path, kept).read_bytes() == b"video"
    assert not upload.part.exists()


# Scenario Outline: An unusable upload is refused and not kept
async def test_accept_refuses_and_deletes_a_bad_upload(tmp_path: Path) -> None:
    uploads, store = _uploads(tmp_path, FakeProber(result=replace(HD, codec="vp9")))
    upload = _part(tmp_path)
    with pytest.raises(SourceError) as error:
        await uploads.accept(upload)
    assert error.value.code == "source_codec_unsupported"
    assert not upload.part.exists() and store.rows == {} and store.commits == 0


# Scenario: Uploads no draft used within 24 hours are swept
async def test_accept_sweeps_old_unused_uploads(tmp_path: Path) -> None:
    uploads, store = _uploads(tmp_path)
    old = source(created_at=NOW - timedelta(hours=25))
    edge = source(created_at=NOW - timedelta(hours=24))
    used = source(created_at=NOW - timedelta(hours=25), repost_id=uuid4())
    for item in (old, edge, used):
        store.rows[item.id] = item
        path = source_path(tmp_path, item)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"old")
    await uploads.accept(_part(tmp_path))
    assert store.deleted == [old.id]
    assert not source_path(tmp_path, old).exists()
    assert source_path(tmp_path, edge).exists()
    assert source_path(tmp_path, used).exists()


_NO_FFMPEG = "ffmpeg is not installed"
_HAS_FFMPEG = shutil.which("ffmpeg") is not None


# Scenario: An H.264 portrait video is stored and gets an asset_id
@pytest.mark.skipif(not _HAS_FFMPEG, reason=_NO_FFMPEG)  # integrity-ok: needs ffmpeg
async def test_ffprobe_reads_a_real_h264_file(tmp_path: Path) -> None:
    video = tmp_path / "v.mp4"
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    process = await asyncio.create_subprocess_exec(
        ffmpeg,
        "-v",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=720x1280:d=3.5",
        "-c:v",
        "libx264",
        str(video),
    )
    assert await process.wait() == 0
    probe = await FfprobeVideoProbe().probe(video)
    assert probe is not None
    assert (probe.codec, probe.width, probe.height) == ("h264", 720, 1280)
    assert 3.0 <= probe.duration_s <= 4.0
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"not a video")
    assert await FfprobeVideoProbe().probe(junk) is None


async def test_ffprobe_missing_binary_reads_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    assert await FfprobeVideoProbe().probe(tmp_path / "v.mp4") is None


@dataclass
class _Sources:
    path_value: Path | None

    async def for_repost(self, repost_id: UUID) -> Path | None:
        del repost_id
        return self.path_value


@dataclass
class _Downloader:
    calls: int = 0

    async def download(self, url: str, target: Path) -> None:
        self.calls += 1
        target.parent.mkdir(parents=True, exist_ok=True)
        if url.endswith(".jpg"):
            Image.new("RGB", (640, 1136)).save(target, format="JPEG")
            return
        target.write_bytes(b"graph")


@dataclass
class _Renderer:
    plan: RenderPlan | None = None

    async def render(self, plan: RenderPlan) -> int:
        self.plan = plan
        Path(plan.output).write_bytes(b"mp4")
        return 3

    async def duration(self, path: str) -> float | None:
        del path
        return 20.0

    async def size(self, path: str) -> tuple[int, int] | None:
        del path
        return (1080, 1920)


def _studio(
    tmp_path: Path, upload: Path | None
) -> tuple[FileRepostStudio, _Downloader, _Renderer]:
    downloader, renderer = _Downloader(), _Renderer()
    config = StudioConfig(
        root=tmp_path / "reposts",
        public_base_url="https://site/",
        downloader=HttpDownloader(httpx.AsyncClient()),
        renderer=FfmpegRenderer(),
        covers=_Covers(),
        sources=_Sources(upload),
    )
    fakes: dict[str, object] = {"downloader": downloader, "renderer": renderer}
    return FileRepostStudio(replace(config, **fakes)), downloader, renderer


@dataclass
class _Covers:
    async def path(self, asset_id: UUID) -> Path | None:
        del asset_id
        return None


def _upload_file(tmp_path: Path) -> Path:
    path = tmp_path / "reposts" / "sources" / "u.mp4"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"hd")
    return path


# Scenario: The worker renders from the upload
async def test_studio_renders_from_the_upload_and_deletes_it(tmp_path: Path) -> None:
    upload = _upload_file(tmp_path)
    studio, downloader, renderer = _studio(tmp_path, upload)
    files = await studio.prepare(StudioJob(repost=stored(), reel=reel()))
    assert renderer.plan is not None and renderer.plan.source == str(upload)
    assert files.preview.is_file() and files.source_size == (1080, 1920)
    assert downloader.calls == 1
    assert not upload.exists()


# Scenario: The worker renders from the upload
async def test_upload_skips_a_missing_graph_video(tmp_path: Path) -> None:
    upload = _upload_file(tmp_path)
    studio, _downloader, renderer = _studio(tmp_path, upload)
    await studio.prepare(
        StudioJob(repost=stored(), reel=replace(reel(), video_url=None))
    )
    assert renderer.plan is not None and renderer.plan.source == str(upload)


# Scenario: A missing upload fails the render
async def test_missing_upload_file_is_source_unavailable(tmp_path: Path) -> None:
    gone = tmp_path / "reposts" / "sources" / "gone.mp4"
    studio, downloader, renderer = _studio(tmp_path, gone)
    with pytest.raises(RepostRenderError) as error:
        await studio.prepare(StudioJob(repost=stored(), reel=reel()))
    assert error.value.code == "source_unavailable"
    assert renderer.plan is None and downloader.calls == 0


async def test_without_upload_the_graph_video_is_downloaded(tmp_path: Path) -> None:
    studio, downloader, renderer = _studio(tmp_path, None)
    await studio.prepare(StudioJob(repost=stored(), reel=reel()))
    assert renderer.plan is not None
    assert renderer.plan.source.endswith("source.mp4")
    assert downloader.calls == 2
    with pytest.raises(RepostRenderError) as error:
        await studio.prepare(
            StudioJob(repost=stored(), reel=replace(reel(), video_url=None))
        )
    assert error.value.code == "source_unavailable"
