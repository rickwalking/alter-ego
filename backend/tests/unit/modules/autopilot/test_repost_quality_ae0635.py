"""Source size in the owner prompt, and the higher-quality encode.

Gherkin: tests/features/autopilot_repost_publish_ae0629.feature
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from rag_backend.modules.autopilot.domain.insights import InsightMetrics
from rag_backend.modules.autopilot.domain.repost_copy import (
    ApprovalNotice,
    approval_text,
    source_line,
)
from rag_backend.modules.autopilot.domain.repost_render import (
    RenderPlan,
    ffmpeg_args,
    ffprobe_size_args,
    parse_size,
    video_filter,
)
from rag_backend.modules.autopilot.infrastructure.repost_video import FfmpegRenderer
from tests.unit.modules.autopilot.repost_fakes import stored

_HAS_FFMPEG = shutil.which("ffmpeg") is not None
_NO_FFMPEG = "ffmpeg is not installed"


# Scenario: The prompt shows the source video's size and warns when it is low
@pytest.mark.parametrize(
    ("size", "warned"),
    [
        ((360, 640), True),
        ((719, 1280), True),
        ((720, 1280), False),
        ((1080, 1920), False),
    ],
)
def test_source_line_warns_below_720p(size: tuple[int, int], warned: bool) -> None:
    line = source_line(size)
    assert f"{size[0]}x{size[1]}" in line
    assert ("⚠️" in line) is warned


# Scenario: The prompt shows the source video's size and warns when it is low
def test_approval_text_carries_the_source_line_only_when_known() -> None:
    repost = stored()
    known = approval_text(
        ApprovalNotice(repost=repost, metrics=InsightMetrics(), source_size=(360, 640))
    )
    assert "Fonte do vídeo: 360x640" in known and "baixa qualidade" in known
    unknown = approval_text(ApprovalNotice(repost=repost, metrics=InsightMetrics()))
    assert "Fonte do vídeo" not in unknown


def test_size_probe_args_and_parsing() -> None:
    args = ffprobe_size_args("/tmp/source.mp4")
    assert args[0] == "ffprobe" and args[-1] == "/tmp/source.mp4"
    assert "stream=width,height" in args and "csv=p=0:s=x" in args
    assert args[args.index("-protocol_whitelist") + 1] == "file,pipe"
    assert parse_size("360x640\n") == (360, 640)
    for bad in ("", "x", "360x", "axb", "360"):
        assert parse_size(bad) is None


# Scenario: The render command
def test_encode_uses_lanczos_crf_20_and_the_medium_preset() -> None:
    assert ":flags=lanczos," in video_filter(None)
    args = ffmpeg_args(
        RenderPlan(
            source="s.mp4", output="o.mp4", trim_start_s=0.0, trim_end_s=None, hook=None
        )
    )
    assert args[args.index("-crf") + 1] == "20"
    assert args[args.index("-preset") + 1] == "medium"


async def test_size_of_a_missing_file_is_none(tmp_path: Path) -> None:
    assert await FfmpegRenderer().size(str(tmp_path / "missing.mp4")) is None


@pytest.mark.skipif(not _HAS_FFMPEG, reason=_NO_FFMPEG)  # integrity-ok: needs ffmpeg
async def test_size_of_a_real_video(tmp_path: Path) -> None:
    source = tmp_path / "s.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=360x640:rate=25",
            "-t",
            "1",
            "-c:v",
            "libx264",
            str(source),
        ],
        check=True,
    )
    assert await FfmpegRenderer().size(str(source)) == (360, 640)
