"""One Chromium export at a time, low-memory flags, image work off the loop.

Feature: backend/tests/features/carousel_generation_load_ae0520.feature
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_backend.application.services.carousel.nodes import export as export_node
from rag_backend.application.services.carousel.nodes.export import (
    BilingualExportConfig,
    render_language,
)
from rag_backend.application.services.pdf_slide_builder import PdfSlideBuilder
from rag_backend.domain.constants import LANGUAGE_PT
from rag_backend.domain.models import CarouselProject
from rag_backend.infrastructure.external import export_lock
from rag_backend.infrastructure.external.playwright_export import (
    CHROMIUM_EXPORT_ARGS,
    PlaywrightExportService,
)

_MODULE = "rag_backend.infrastructure.external.playwright_export"
_HTML = "<html><div class='ig-slide-inner'></div></html>"


@dataclass
class _Tracker:
    """Counts Chromium instances open at once."""

    active: int = 0
    peak: int = 0
    launches: list[tuple[str, ...]] = field(default_factory=list)
    fail_first: bool = False

    def playwright(self) -> MagicMock:
        tracker = self

        async def screenshot(**_kwargs: object) -> None:
            await asyncio.sleep(0.01)

        async def close() -> None:
            tracker.active -= 1

        async def launch(*, args: list[str]) -> MagicMock:
            tracker.launches.append(tuple(args))
            if tracker.fail_first and len(tracker.launches) == 1:
                raise RuntimeError("chromium crashed")
            tracker.active += 1
            tracker.peak = max(tracker.peak, tracker.active)
            await asyncio.sleep(0.01)
            element = MagicMock()
            element.screenshot = screenshot
            locator = MagicMock()
            locator.all = AsyncMock(return_value=[element])
            page = MagicMock()
            page.goto = AsyncMock()
            page.evaluate = AsyncMock()
            page.locator = MagicMock(return_value=locator)
            browser = MagicMock()
            browser.new_page = AsyncMock(return_value=page)
            browser.close = close
            return browser

        manager = MagicMock()
        manager.chromium.launch = launch
        manager.__aenter__ = AsyncMock(return_value=manager)
        manager.__aexit__ = AsyncMock(return_value=None)
        return manager


@contextmanager
def _fake_chromium(tracker: _Tracker) -> Iterator[None]:
    with (
        patch(f"{_MODULE}.async_playwright", side_effect=tracker.playwright),
        patch(f"{_MODULE}.run_export_preflight", new_callable=AsyncMock),
        patch(f"{_MODULE}._crop_border_artifact"),
    ):
        yield


async def _export(out: Path) -> list[str]:
    return await PlaywrightExportService.export_slides(_HTML, str(out))


@pytest.mark.unit
async def test_two_concurrent_exports_run_one_chromium_at_a_time(
    tmp_path: Path,
) -> None:
    """Scenario: Two carousels exporting at the same time run one Chromium export
    at a time.
    """
    tracker = _Tracker()

    with _fake_chromium(tracker):
        first, second = await asyncio.gather(
            _export(tmp_path / "a"), _export(tmp_path / "b")
        )

    assert tracker.peak == 1
    assert len(tracker.launches) == 2
    assert first == [str(tmp_path / "a" / "slide_1.jpg")]
    assert second == [str(tmp_path / "b" / "slide_1.jpg")]


@pytest.mark.unit
async def test_failed_export_releases_the_slot(tmp_path: Path) -> None:
    """Scenario: An export that fails releases the slot for the next one."""
    tracker = _Tracker(fail_first=True)

    with _fake_chromium(tracker):
        results = await asyncio.gather(
            _export(tmp_path / "a"), _export(tmp_path / "b"), return_exceptions=True
        )

    assert isinstance(results[0], RuntimeError)
    assert results[1] == [str(tmp_path / "b" / "slide_1.jpg")]
    assert len(tracker.launches) == 2


@pytest.mark.unit
async def test_chromium_launches_with_low_memory_flags(tmp_path: Path) -> None:
    """Scenario: The exporter launches Chromium with the low-memory flags."""
    tracker = _Tracker()

    with _fake_chromium(tracker):
        await _export(tmp_path)

    assert tracker.launches == [CHROMIUM_EXPORT_ARGS]
    assert CHROMIUM_EXPORT_ARGS == (
        "--disable-dev-shm-usage",
        "--renderer-process-limit=1",
    )


@pytest.mark.unit
async def test_slot_without_postgres_uses_only_the_process_lock() -> None:
    """Scenario: Two carousels exporting at the same time run one Chromium export
    at a time.
    """
    with patch.object(export_lock.database_config, "c_engine", None):
        async with export_lock.export_slot():
            assert export_lock._process_lock().locked()
    assert not export_lock._process_lock().locked()


@pytest.mark.unit
async def test_slot_ignores_a_non_postgres_engine() -> None:
    """Scenario: Two carousels exporting at the same time run one Chromium export
    at a time.
    """
    engine = MagicMock()
    engine.dialect.name = "sqlite"
    with patch.object(export_lock.database_config, "c_engine", engine):
        async with export_lock.export_slot():
            engine.connect.assert_not_called()


@pytest.mark.unit
async def test_crop_runs_in_a_worker_thread(tmp_path: Path) -> None:
    """Scenario: Image cropping and the PDF build run off the event loop."""
    loop_thread = threading.get_ident()
    crop_threads: list[int] = []

    def crop(path: str, width: int, height: int) -> None:
        crop_threads.append(threading.get_ident())
        assert (width, height) == (1080, 1350)

    tracker = _Tracker()
    with (
        patch(f"{_MODULE}.async_playwright", side_effect=tracker.playwright),
        patch(f"{_MODULE}.run_export_preflight", new_callable=AsyncMock),
        patch(f"{_MODULE}._crop_border_artifact", side_effect=crop),
    ):
        await PlaywrightExportService.export_slides(_HTML, str(tmp_path))

    assert len(crop_threads) == 1
    assert crop_threads[0] != loop_thread


@pytest.mark.unit
async def test_assets_and_pdf_build_run_in_worker_threads(tmp_path: Path) -> None:
    """Scenario: Image cropping and the PDF build run off the event loop."""
    loop_thread = threading.get_ident()
    asset_threads: list[int] = []
    pdf_threads: list[int] = []

    def build(slide_paths: list[str], output_dir: str) -> str:
        pdf_threads.append(threading.get_ident())
        return f"{output_dir}/carousel.pdf"

    export = MagicMock()
    export.export_slides = AsyncMock(return_value=[str(tmp_path / "slide_1.jpg")])
    project = CarouselProject(topic="t", audience="a", niche="n")
    config = BilingualExportConfig(
        project=project,
        slides_data=[],
        pt_html=_HTML,
        output_dir=tmp_path,
        export=export,
        pdf_builder=PdfSlideBuilder(),
        language=LANGUAGE_PT,
        html_content=_HTML,
    )

    with (
        patch.object(
            export_node,
            "prepare_carousel_export_assets",
            side_effect=lambda _dir: asset_threads.append(threading.get_ident()),
        ),
        patch.object(PdfSlideBuilder, "build", side_effect=build),
    ):
        await render_language(config)

    assert len(asset_threads) == 1
    assert asset_threads[0] != loop_thread
    assert len(pdf_threads) == 1
    assert pdf_threads[0] != loop_thread
    assert project.pdf_path == f"{tmp_path / LANGUAGE_PT}/carousel.pdf"
