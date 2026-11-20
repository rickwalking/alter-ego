"""The ffmpeg command, the video adapters and the repost studio.

Gherkin: tests/features/autopilot_repost_publish_ae0629.feature
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from PIL import Image

from rag_backend.modules.autopilot.application.repost_tick_ports import (
    RepostRenderError,
    StudioJob,
)
from rag_backend.modules.autopilot.domain.repost_render import (
    HookOverlay,
    RenderPlan,
    ffmpeg_args,
    ffprobe_args,
    ffprobe_file_args,
    parse_duration,
    video_filter,
    wrap_hook,
)
from rag_backend.modules.autopilot.infrastructure import repost_video
from rag_backend.modules.autopilot.infrastructure.repost_studio import (
    FileRepostStudio,
    StudioConfig,
)
from rag_backend.modules.autopilot.infrastructure.repost_video import (
    FfmpegRenderer,
    FfprobeReelProbe,
    HttpDownloader,
    RenderError,
    repost_dir,
    reposts_dir,
    write_jpeg,
)
from tests.unit.modules.autopilot.repost_fakes import reel, stored

_HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


# Scenario: The render command
def test_ffmpeg_command_trims_scales_and_draws_the_hook() -> None:
    hook = HookOverlay(
        line_files=("/t/hook_0.txt", "/t/hook_1.txt"),
        duration_s=2.5,
        font_file="/f:o'nt.ttf",
    )
    args = ffmpeg_args(
        RenderPlan(
            source="in.mp4", output="out.mp4", trim_start_s=1, trim_end_s=6.5, hook=hook
        )
    )
    joined = " ".join(args)
    assert args[0] == "ffmpeg" and args[-1] == "out.mp4"
    assert (
        args[args.index("-ss") + 1] == "1.000"
        and args[args.index("-to") + 1] == "6.500"
    )
    for part in ("libx264", "aac", "-maxrate", "+faststart", "0:a:0?", "file,pipe"):
        assert part in joined
    vf = args[args.index("-vf") + 1]
    assert "scale=1080:1920" in vf and "pad=1080:1920" in vf and "fps=30" in vf
    assert vf.count("drawtext=") == 2
    assert "expansion=none" in vf and "lt(t,2.500)" in vf
    assert "/f\\:o\\'nt.ttf" in vf


def test_ffmpeg_command_without_hook_or_trim_end() -> None:
    args = ffmpeg_args(
        RenderPlan(source="in.mp4", output="out.mp4", trim_start_s=0, trim_end_s=None)
    )
    assert "-to" not in args
    assert "drawtext" not in video_filter(None)
    assert "drawtext" not in video_filter(
        HookOverlay(line_files=(), duration_s=1, font_file="f")
    )


def test_wrap_and_probe_helpers() -> None:
    lines = wrap_hook("Sua IA aprova o próprio código ruim. E a culpa não é dela.")
    assert len(lines) > 1 and all(len(line) <= 22 for line in lines)
    assert wrap_hook("   ") == ()
    assert "https,tls,tcp" in ffprobe_args("https://x")
    assert "file,pipe" in ffprobe_file_args("/x.mp4")
    assert parse_duration("12.5\n") == 12.5
    assert parse_duration("N/A") is None
    assert parse_duration("") is None
    assert parse_duration("-1") is None


def test_paths() -> None:
    root = reposts_dir("./output/carousels")
    assert root.name == "reposts" and root.parent.name == "output"
    repost_id = UUID(int=1)
    assert repost_dir(root, repost_id).name == str(repost_id)


async def test_probe_refuses_non_https_and_missing_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = FfprobeReelProbe()
    assert await probe.duration("file:///etc/passwd") is None
    monkeypatch.setattr(repost_video.shutil, "which", lambda _name: None)
    assert await probe.duration("https://x/v.mp4") is None
    with pytest.raises(RenderError) as error:
        await FfmpegRenderer().render(
            RenderPlan(source="a", output="b", trim_start_s=0, trim_end_s=None)
        )
    assert error.value.code == "render_unavailable"


async def test_probe_failure_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom(run: object) -> str:
        raise RenderError("render_failed")

    monkeypatch.setattr(repost_video.shutil, "which", lambda _name: "/bin/true")
    monkeypatch.setattr(repost_video, "_run", boom)
    assert await FfprobeReelProbe().duration("https://x/v.mp4") is None
    assert await FfmpegRenderer().duration("/x.mp4") is None


async def test_run_errors() -> None:
    with pytest.raises(RenderError) as error:
        await repost_video._run(
            repost_video._Run(args=["/nonexistent/binary"], timeout=1)
        )
    assert error.value.code == "render_unavailable"
    with pytest.raises(RenderError) as error:
        await repost_video._run(repost_video._Run(args=["false"], timeout=5))
    assert error.value.code == "render_failed"
    with pytest.raises(RenderError):
        await repost_video._run(repost_video._Run(args=["sleep", "5"], timeout=0.05))
    assert (
        await repost_video._run(repost_video._Run(args=["echo", "1.5"], timeout=5))
    ).strip() == "1.5"


async def test_renderer_missing_output_and_too_large(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def ok(run: object) -> str:
        return ""

    monkeypatch.setattr(repost_video.shutil, "which", lambda _name: "/bin/true")
    monkeypatch.setattr(repost_video, "_run", ok)
    plan = RenderPlan(
        source="a", output=str(tmp_path / "out.mp4"), trim_start_s=0, trim_end_s=None
    )
    with pytest.raises(RenderError) as error:
        await FfmpegRenderer().render(plan)
    assert error.value.code == "render_failed"
    (tmp_path / "out.mp4").write_bytes(b"x" * 20)
    with pytest.raises(RenderError) as error:
        await FfmpegRenderer(max_bytes=10).render(plan)
    assert error.value.code == "render_too_large"
    assert not (tmp_path / "out.mp4").exists()
    (tmp_path / "out.mp4").write_bytes(b"x" * 5)
    assert await FfmpegRenderer(max_bytes=10).render(plan) == 5


def _transport(body: bytes, status: int = 200) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _r: httpx.Response(status, content=body))
    )


async def test_downloader(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async with _transport(b"video") as client:
        target = tmp_path / "a" / "s.mp4"
        await HttpDownloader(client).download("https://cdn/v.mp4", target)
        assert target.read_bytes() == b"video"
        with pytest.raises(RenderError):
            await HttpDownloader(client).download("http://cdn/v.mp4", target)
    async with _transport(b"", status=403) as client:
        with pytest.raises(RenderError) as error:
            await HttpDownloader(client).download(
                "https://cdn/v.mp4", tmp_path / "b.mp4"
            )
    assert error.value.code == "source_unavailable"
    assert not (tmp_path / "b.mp4").exists()
    monkeypatch.setattr(repost_video, "DOWNLOAD_MAX_BYTES", 3)
    async with _transport(b"toolong") as client:
        with pytest.raises(RenderError):
            await HttpDownloader(client).download(
                "https://cdn/v.mp4", tmp_path / "c.mp4"
            )


def test_write_jpeg_pads_to_9_16(tmp_path: Path) -> None:
    source = tmp_path / "c.webp"
    Image.new("RGBA", (100, 100), (255, 0, 0, 128)).save(source)
    target = tmp_path / "out" / "c.jpg"
    write_jpeg(source, target)
    with Image.open(target) as image:
        assert (image.format, image.size) == ("JPEG", (1080, 1920))


@dataclass
class _Covers:
    path_value: Path | None

    async def path(self, asset_id: UUID) -> Path | None:
        del asset_id
        return self.path_value


@dataclass
class _FakeDownloader:
    payload: bytes = b"src"
    fail_on: str | None = None

    async def download(self, url: str, target: Path) -> None:
        if self.fail_on is not None and self.fail_on in url:
            raise RenderError("source_unavailable")
        target.parent.mkdir(parents=True, exist_ok=True)
        if url.endswith(".jpg"):
            Image.new("RGB", (640, 1136)).save(target, format="JPEG")
            return
        target.write_bytes(self.payload)


@dataclass
class _FakeRenderer:
    seconds: float | None = 10.0
    fail: str | None = None

    async def render(self, plan: RenderPlan) -> int:
        if self.fail:
            raise RenderError(self.fail)
        Path(plan.output).write_bytes(b"mp4")
        self.plan = plan
        return 3

    async def duration(self, path: str) -> float | None:
        del path
        return self.seconds


def _studio(tmp_path: Path, **changes: object) -> FileRepostStudio:
    cover = tmp_path / "grok.webp"
    Image.new("RGB", (1080, 1920)).save(cover)
    config = StudioConfig(
        root=tmp_path / "reposts",
        public_base_url="https://site/",
        downloader=_FakeDownloader(),
        renderer=_FakeRenderer(),
        covers=_Covers(cover),
        font_file=_FONT,
    )
    return FileRepostStudio(replace(config, **changes))


# Scenario: A pending draft is rendered and sent to the owner
async def test_studio_writes_preview_and_both_covers(tmp_path: Path) -> None:
    studio = _studio(tmp_path)
    repost = stored(cover_asset_id=UUID(int=7))
    files = await studio.prepare(StudioJob(repost=repost, reel=reel()))
    assert files.preview.name == "preview.mp4" and files.fits_telegram
    assert files.cover is not None and files.cover.is_file()
    assert files.original_cover is not None and files.original_cover.is_file()
    folder = repost_dir(tmp_path / "reposts", repost.id)
    assert not (folder / "source.mp4").exists()
    assert (folder / "hook_0.txt").read_text() == "Gancho"
    assert (
        studio.public_url(repost, "preview.mp4")
        == f"https://site/r/{repost.id}/preview.mp4"
    )
    assert studio.existing(repost, "cover.jpg") is not None
    assert studio.existing(repost, "nope.jpg") is None


async def test_studio_without_hook_cover_or_thumbnail(tmp_path: Path) -> None:
    studio = _studio(tmp_path, covers=_Covers(None))
    repost = stored(hook_text=None, cover_asset_id=UUID(int=7))
    files = await studio.prepare(
        StudioJob(repost=repost, reel=replace(reel(), thumbnail_url=None))
    )
    assert files.cover is None and files.original_cover is None
    files = await _studio(tmp_path).prepare(
        StudioJob(repost=stored(hook_text=None), reel=reel())
    )
    assert files.cover is None


async def test_studio_original_cover_download_failure_is_tolerated(
    tmp_path: Path,
) -> None:
    studio = _studio(tmp_path, downloader=_FakeDownloader(fail_on=".jpg"))
    files = await studio.prepare(StudioJob(repost=stored(), reel=reel()))
    assert files.original_cover is None


# Scenario: A failed render ends the draft without messaging the owner
@pytest.mark.parametrize(
    ("renderer", "code"),
    [
        (_FakeRenderer(fail="render_failed"), "render_failed"),
        (_FakeRenderer(seconds=2.0), "render_duration_invalid"),
        (_FakeRenderer(seconds=91.0), "render_duration_invalid"),
        (_FakeRenderer(seconds=None), "render_duration_invalid"),
    ],
)
async def test_studio_render_failures(
    tmp_path: Path, renderer: _FakeRenderer, code: str
) -> None:
    studio = _studio(tmp_path, renderer=renderer)
    with pytest.raises(RepostRenderError) as error:
        await studio.prepare(StudioJob(repost=stored(), reel=reel()))
    assert error.value.code == code


@pytest.mark.skipif(
    not _HAS_FFMPEG, reason="ffmpeg is not installed"
)  # integrity-ok: needs the ffmpeg binary, present in the prod image and dev machines, not on CI runners
async def test_real_render_end_to_end(tmp_path: Path) -> None:
    source = tmp_path / "src.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x568:rate=25",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440",
            "-t",
            "5",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            str(source),
        ],
        check=True,
    )
    downloader = _FakeDownloader(payload=source.read_bytes())
    studio = _studio(tmp_path, downloader=downloader, renderer=FfmpegRenderer())
    repost = stored(
        hook_text="Gancho 100% 'real': teste", trim_start_s=0.5, trim_end_s=4.5
    )
    files = await studio.prepare(StudioJob(repost=repost, reel=reel()))
    seconds = await FfmpegRenderer().duration(str(files.preview))
    assert seconds is not None and 3.5 <= seconds <= 4.5
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,codec_name",
            "-of",
            "csv=p=0",
            str(files.preview),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert probe.stdout.strip() == "h264,1080,1920"
