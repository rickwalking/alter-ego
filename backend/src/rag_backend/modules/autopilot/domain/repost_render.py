"""The ffmpeg and ffprobe argument lists for a repost. Pure; no process runs here.

One pass: trim, scale and pad to 1080x1920, 30 fps, H.264 (bounded bitrate)
and AAC, the hook burnt in for its first seconds from a text file (so no
caption text is ever parsed as filter syntax), and ``+faststart``.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass

from rag_backend.modules.autopilot.reels_constants import FFMPEG_BINARY, FFPROBE_BINARY
from rag_backend.modules.autopilot.repost_constants import (
    HOOK_BOX_ALPHA,
    HOOK_BOX_BORDER,
    HOOK_FONT_SIZE,
    HOOK_LINE_CHARS,
    HOOK_LINE_SPACING,
    HOOK_TOP_RATIO,
    RENDER_AUDIO_BITRATE,
    RENDER_AUDIO_RATE,
    RENDER_BUFSIZE,
    RENDER_CRF,
    RENDER_FPS,
    RENDER_HEIGHT,
    RENDER_MAXRATE,
    RENDER_PRESET,
    RENDER_THREADS,
    RENDER_WIDTH,
)

_PROTOCOLS_FILE = "file,pipe"
_PROTOCOLS_HTTPS = "https,tls,tcp"


@dataclass(frozen=True, kw_only=True)
class HookOverlay:
    """One text file per hook line, how long it shows, and the font."""

    line_files: tuple[str, ...]
    duration_s: float
    font_file: str


@dataclass(frozen=True, kw_only=True)
class RenderPlan:
    """Input and output files, the trim, and the optional hook."""

    source: str
    output: str
    trim_start_s: float
    trim_end_s: float | None
    hook: HookOverlay | None = None


def wrap_hook(text: str) -> tuple[str, ...]:
    """The hook broken into lines that fit the 1080 px frame."""
    return tuple(textwrap.wrap(text.strip(), width=HOOK_LINE_CHARS))


def video_filter(hook: HookOverlay | None) -> str:
    """Scale and pad to 9:16, fix the frame rate, then draw the hook."""
    base = (
        f"scale={RENDER_WIDTH}:{RENDER_HEIGHT}:force_original_aspect_ratio=decrease"
        ":flags=lanczos,"
        f"pad={RENDER_WIDTH}:{RENDER_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"setsar=1,fps={RENDER_FPS}"
    )
    if hook is None or not hook.line_files:
        return base
    lines = (
        _drawtext(hook, _Line(path=path, index=index))
        for index, path in enumerate(hook.line_files)
    )
    return ",".join((base, *lines))


def ffmpeg_args(plan: RenderPlan) -> list[str]:
    """The full ffmpeg command for one render."""
    args = [FFMPEG_BINARY, "-nostdin", "-y", "-hide_banner", "-loglevel", "error"]
    args += ["-protocol_whitelist", _PROTOCOLS_FILE]
    args += ["-ss", _seconds(plan.trim_start_s)]
    if plan.trim_end_s is not None:
        args += ["-to", _seconds(plan.trim_end_s)]
    args += ["-i", plan.source, "-map", "0:v:0", "-map", "0:a:0?"]
    args += ["-vf", video_filter(plan.hook)]
    args += _encoder_args()
    args.append(plan.output)
    return args


def ffprobe_args(url: str) -> list[str]:
    """Read the duration of an https video (no other protocol is allowed)."""
    return _probe(url, _PROTOCOLS_HTTPS)


def ffprobe_file_args(path: str) -> list[str]:
    """Read the duration of a local file."""
    return _probe(path, _PROTOCOLS_FILE)


def _probe(source: str, protocols: str) -> list[str]:
    return [
        FFPROBE_BINARY,
        "-v",
        "error",
        "-protocol_whitelist",
        protocols,
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        source,
    ]


def ffprobe_size_args(path: str) -> list[str]:
    """Read the first video stream's width and height of a local file."""
    return [
        FFPROBE_BINARY,
        "-v",
        "error",
        "-protocol_whitelist",
        _PROTOCOLS_FILE,
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0:s=x",
        path,
    ]


def parse_size(output: str) -> tuple[int, int] | None:
    """ffprobe's ``WIDTHxHEIGHT`` line, or None."""
    width, _sep, height = output.strip().partition("x")
    if not (width.isdigit() and height.isdigit()):
        return None
    return int(width), int(height)


def parse_duration(output: str) -> float | None:
    """ffprobe's duration line as seconds, or None."""
    try:
        value = float(output.strip().splitlines()[0])
    except (ValueError, IndexError):
        return None
    return value if value > 0 else None


@dataclass(frozen=True, kw_only=True)
class _Line:
    path: str
    index: int


def _drawtext(hook: HookOverlay, line: _Line) -> str:
    step = HOOK_FONT_SIZE + HOOK_LINE_SPACING + 2 * HOOK_BOX_BORDER
    return (
        f"drawtext=fontfile='{_escaped(hook.font_file)}'"
        f":textfile='{_escaped(line.path)}'"
        f":expansion=none:fontsize={HOOK_FONT_SIZE}:fontcolor=white"
        f":box=1:boxcolor=black@{HOOK_BOX_ALPHA}:boxborderw={HOOK_BOX_BORDER}"
        f":x=(w-text_w)/2:y=h*{HOOK_TOP_RATIO}+{line.index * step}"
        f":enable='lt(t,{_seconds(hook.duration_s)})'"
    )


def _encoder_args() -> list[str]:
    return [
        "-c:v",
        "libx264",
        "-preset",
        RENDER_PRESET,
        "-crf",
        RENDER_CRF,
        "-maxrate",
        RENDER_MAXRATE,
        "-bufsize",
        RENDER_BUFSIZE,
        "-profile:v",
        "high",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        RENDER_AUDIO_BITRATE,
        "-ar",
        RENDER_AUDIO_RATE,
        "-threads",
        RENDER_THREADS,
        "-movflags",
        "+faststart",
    ]


def _seconds(value: float) -> str:
    return f"{value:.3f}"


def _escaped(path: str) -> str:
    return path.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:")


__all__ = [
    "HookOverlay",
    "RenderPlan",
    "ffmpeg_args",
    "ffprobe_args",
    "ffprobe_file_args",
    "parse_duration",
    "video_filter",
    "wrap_hook",
]
