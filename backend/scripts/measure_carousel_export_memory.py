"""Measure the generation worker's memory across carousel images/export cycles.

WHY THIS EXISTS
---------------
The generation worker kept memory between carousel runs and peaked at its cap in
the images/export step. This script replays that step N times in one process, the
way the long-lived worker does, and reports the memory after every cycle, so a
retention shows up as a rising baseline and a fix as a flat one.

WHAT ONE CYCLE DOES
-------------------
1. Images: a generated test picture (no paid provider) goes through the image bridge
   codec (validate + normalize to the bridge size) and the images node's JPEG check,
   one per artwork slide, written under ``<output>/images/``.
2. Export: the real bilingual export (PT then EN; standard then HD per language,
   real headless Chromium) and the img2pdf build.
3. Artifact: the real artifact adapter builds, promotes and activates the version
   (staging copies, manifest hashes, ``current.json``); only the database is faked.
4. The cycle's output directory is removed, unless ``--keep``.

WHAT IT REPORTS (one JSON line per cycle)
-----------------------------------------
``rss_mib`` / ``anon_mib``: the Python process after the cycle. ``tracemalloc_mib`` /
``tracemalloc_peak_mib``: Python-level allocations. ``tree_peak_mib``: the highest sum
of the process tree's anonymous memory seen during the cycle (Python, the Playwright
driver and Chromium). When the process runs in its own cgroup (a container, or
``systemd-run --user --scope``): ``cgroup_peak_mib`` during the cycle, and
``cgroup_mib`` with its ``anon``/``file``/``shmem`` split after it.

USAGE (inside the backend image, capped like the worker)
    docker run --rm -m 1600m --memory-swap 1600m --tmpfs /tmp:size=512m \\
        --entrypoint python <backend image> \\
        scripts/measure_carousel_export_memory.py --cycles 6 --output /app/output/measure
"""

from __future__ import annotations

import argparse
import asyncio
import gc
import io
import json
import os
import shutil
import threading
import time
import tracemalloc
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.carousel.nodes.design import run_design
from rag_backend.application.services.carousel.nodes.export import (
    BilingualExportConfig,
    run_bilingual_export,
)
from rag_backend.application.services.carousel.nodes.images import (
    _ensure_jpeg_format,
)
from rag_backend.application.services.carousel.types import SlideData
from rag_backend.application.services.carousel_template import CarouselTemplateBuilder
from rag_backend.application.services.pdf_slide_builder import PdfSlideBuilder
from rag_backend.domain.models import CarouselProject, CarouselSlide
from rag_backend.infrastructure.external.playwright_export import (
    PlaywrightExportService,
)
from rag_backend.modules.image_bridge.domain.ports import NormalizeRequest
from rag_backend.modules.image_bridge.infrastructure.pillow_codec import (
    PillowImageCodec,
)
from rag_backend.modules.presentation.infrastructure.editorial_workflow_ports import (
    CarouselArtifactBuildAdapter,
)

_MIB = 1024 * 1024
_KIB_PER_MIB = 1024
_SAMPLE_SECONDS = 0.05
_SOURCE_SIZE = (1024, 1536)
_BRIDGE_SIZE = (1536, 1024)
_CGROUP_ROOT = Path("/sys/fs/cgroup")
_CGROUP_STAT_KEYS = ("anon", "file", "shmem")
_PROC_ANON_KEYS = ("RssAnon:", "RssShmem:")
_BUILD_MODULE = "rag_backend.application.services.carousel.artifact_build_service"
_BUILD_REPO = f"{_BUILD_MODULE}.PostgresCarouselArtifactBuildRepository"
_LOCK_READER = f"{_BUILD_MODULE}.read_project_lock_version"


def _proc_kib(pid: int, keys: tuple[str, ...]) -> int:
    """The sum of the ``/proc/<pid>/status`` fields named in ``keys`` (KiB)."""
    try:
        lines = Path(f"/proc/{pid}/status").read_text().splitlines()
    except OSError:
        return 0
    total = 0
    for line in lines:
        parts = line.split()
        if parts and parts[0] in keys:
            total += int(parts[1])
    return total


def _children(pid: int) -> list[int]:
    """Direct children of ``pid`` across its threads."""
    found: list[int] = []
    try:
        tasks = list(Path(f"/proc/{pid}/task").iterdir())
    except OSError:
        return found
    for task in tasks:
        try:
            found.extend(int(c) for c in (task / "children").read_text().split())
        except OSError:
            continue
    return found


def _tree(pid: int) -> list[int]:
    """``pid`` and every descendant."""
    pids = [pid]
    for child in _children(pid):
        pids.extend(_tree(child))
    return pids


def _cgroup_dir() -> Path | None:
    """This process's cgroup v2 directory when it exposes memory files."""
    try:
        entry = Path("/proc/self/cgroup").read_text().strip().split(":", 2)[2]
    except (OSError, IndexError):
        return None
    candidate = _CGROUP_ROOT / entry.lstrip("/")
    if (candidate / "memory.current").is_file():
        return candidate
    return None


def _cgroup_mib(cgroup: Path) -> int:
    return int((cgroup / "memory.current").read_text()) // _MIB


def _cgroup_split(cgroup: Path) -> dict[str, int]:
    stats: dict[str, int] = {}
    for line in (cgroup / "memory.stat").read_text().splitlines():
        key, value = line.split()
        if key in _CGROUP_STAT_KEYS:
            stats[key] = int(value) // _MIB
    return stats


@dataclass
class _PeakSampler:
    """Polls the process tree (and the cgroup) until stopped, keeping the peaks."""

    cgroup: Path | None
    tree_peak_mib: int = 0
    cgroup_peak_mib: int = 0
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()

    def _run(self) -> None:
        me = os.getpid()
        while not self._stop.is_set():
            tree = sum(_proc_kib(pid, _PROC_ANON_KEYS) for pid in _tree(me))
            self.tree_peak_mib = max(self.tree_peak_mib, tree // _KIB_PER_MIB)
            if self.cgroup is not None:
                self.cgroup_peak_mib = max(
                    self.cgroup_peak_mib, _cgroup_mib(self.cgroup)
                )
            time.sleep(_SAMPLE_SECONDS)


def _slides(count: int) -> list[SlideData]:
    """A ``count``-slide deck with EN translations, so both languages render."""
    slides: list[SlideData] = []
    for number in range(1, count + 1):
        if number == 1:
            slide_type = "intro"
        elif number == count:
            slide_type = "cta"
        elif number == count - 1:
            slide_type = "closing"
        else:
            slide_type = "content"
        slides.append(
            SlideData(
                slide_number=number,
                slide_type=slide_type,
                heading=f"Titulo do slide {number} sobre agentes de IA",
                body="Texto do corpo do slide com frases reais de tamanho medio. " * 2,
                image_prompt=f"editorial illustration {number}",
                translation_en={
                    "heading": f"Slide {number} heading about AI agents",
                    "body": "Body copy of the slide with medium sized sentences. " * 2,
                },
            )
        )
    return slides


def _source_image(seed: int) -> bytes:
    """A generated picture the size of a provider image (PNG, like the bridge)."""
    span = 0.002 * seed
    image = Image.effect_mandelbrot(
        _SOURCE_SIZE, (-2.0 + span, -1.5, 1.0 + span, 1.5), 96
    ).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _write_images(images_dir: Path, count: int, cycle: int) -> None:
    """Run each test picture through the bridge codec and the node's JPEG check."""
    images_dir.mkdir(parents=True, exist_ok=True)
    codec = PillowImageCodec()
    for number in range(1, count + 1):
        source = _source_image(cycle * count + number)
        codec.validate(source)
        png = codec.normalize(NormalizeRequest(source, *_BRIDGE_SIZE))
        target = images_dir / f"slide_{number}.jpg"
        target.write_bytes(png)
        _ensure_jpeg_format(str(target))


class _ProjectRepository:
    """The carousel repository the artifact adapter reads, backed by memory."""

    def __init__(self, project: CarouselProject, slide_count: int) -> None:
        self._project = project
        self._slides = [
            CarouselSlide(
                project_id=project.id,
                slide_number=number,
                slide_type="content",
                heading=f"Heading {number}",
                body=f"Body {number}",
            )
            for number in range(1, slide_count + 1)
        ]

    async def get_project_by_id(self, project_id: UUID) -> CarouselProject | None:
        del project_id
        return self._project

    async def get_slides_by_project(self, project_id: UUID) -> list[CarouselSlide]:
        del project_id
        return self._slides


async def _activate_artifact(project: CarouselProject, slide_count: int) -> None:
    """Run the real artifact adapter with an in-memory build table and session."""
    build_repo = MagicMock()
    build_repo.get_by_project_and_version = AsyncMock(return_value=None)
    build_repo.upsert_build = AsyncMock(side_effect=lambda build: build)
    build_repo.activate_build = AsyncMock(return_value=1)
    session = MagicMock()
    session.commit = AsyncMock()
    adapter = CarouselArtifactBuildAdapter(
        db=cast("AsyncSession", session),
        repository=_ProjectRepository(project, slide_count),
    )
    with (
        patch(_BUILD_REPO, return_value=build_repo),
        patch(_LOCK_READER, AsyncMock(return_value=0)),
    ):
        activation = await adapter.build_and_activate(str(project.id))
    if not activation.ok:
        raise RuntimeError(activation.errors)


async def _cycle(output: Path, slide_count: int, cycle: int) -> None:
    images_dir = output / "images"
    await asyncio.to_thread(_write_images, images_dir, slide_count, cycle)
    project = CarouselProject(
        topic="memoria", audience="devs", niche="ia", output_dir=str(output)
    )
    slides = _slides(slide_count)
    template = CarouselTemplateBuilder()
    html = run_design(project, slides, template=template)
    await run_bilingual_export(
        BilingualExportConfig(
            project=project,
            slides_data=slides,
            pt_html=html,
            output_dir=output,
            export=PlaywrightExportService(),
            pdf_builder=PdfSlideBuilder(),
            template=template,
        )
    )
    await _activate_artifact(project, slide_count)


def _report(cycle: int, seconds: float, sampler: _PeakSampler) -> dict[str, object]:
    me = os.getpid()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    row: dict[str, object] = {
        "cycle": cycle,
        "seconds": round(seconds, 1),
        "rss_mib": _proc_kib(me, ("VmRSS:",)) // _KIB_PER_MIB,
        "anon_mib": _proc_kib(me, ("RssAnon:",)) // _KIB_PER_MIB,
        "tracemalloc_mib": current // _MIB,
        "tracemalloc_peak_mib": peak // _MIB,
        "tree_peak_mib": sampler.tree_peak_mib,
    }
    if sampler.cgroup is not None:
        row["cgroup_peak_mib"] = sampler.cgroup_peak_mib
        row["cgroup_mib"] = _cgroup_mib(sampler.cgroup)
        row.update({
            f"cgroup_{k}_mib": v for k, v in _cgroup_split(sampler.cgroup).items()
        })
    return row


async def _main(args: argparse.Namespace) -> None:
    tracemalloc.start()
    cgroup = _cgroup_dir()
    print(json.dumps({"cycle": 0, **_report(0, 0.0, _PeakSampler(cgroup))}))
    for cycle in range(1, args.cycles + 1):
        output = Path(args.output) / f"cycle-{cycle}"
        sampler = _PeakSampler(cgroup)
        sampler.start()
        started = time.monotonic()
        await _cycle(output, args.slides, cycle)
        sampler.stop()
        if not args.keep:
            shutil.rmtree(output, ignore_errors=True)
        gc.collect()
        print(
            json.dumps(_report(cycle, time.monotonic() - started, sampler)),
            flush=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cycles", type=int, default=5)
    parser.add_argument("--slides", type=int, default=10)
    parser.add_argument("--output", required=True)
    parser.add_argument("--keep", action="store_true")
    asyncio.run(_main(parser.parse_args()))


if __name__ == "__main__":
    main()
