"""Exact-behaviour tests for the bilingual export node (render + fan-out).

Feature: Bilingual carousel slide export (PT + EN slides, HD archive, PDF)
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from rag_backend.application.services.carousel.nodes.export import (
    BilingualExportConfig,
    render_language,
    rewrite_asset_paths,
    run_bilingual_export,
)
from rag_backend.application.services.carousel.types import (
    SlideData,
    slides_data_for_language,
)
from rag_backend.domain.constants import (
    HD_SUBDIR_NAME,
    LANGUAGE_EN,
    LANGUAGE_PT,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols import ExportConfig

_EXPORT = "rag_backend.application.services.carousel.nodes.export"
_POLICY_VERSION = "v2"
_PROJECT_SLIDE_COUNT = 7
_HTML = "<html>body</html>"
_PDF_PATH = "/out/carousel.pdf"
_SLIDE_PATHS = ["/out/slide_1.jpg", "/out/slide_2.jpg"]
_HD_FAILED_EVENT = "hd_export_failed"
_PDF_FAILED_EVENT = "carousel_pdf_build_failed"
_PDF_ERROR = "pdf exploded"


def _project() -> CarouselProject:
    return CarouselProject(
        topic="T",
        audience="A",
        niche="N",
        presentation_policy_version=_POLICY_VERSION,
        slide_count=_PROJECT_SLIDE_COUNT,
    )


def _slides(count: int, *, translated: bool = False) -> list[SlideData]:
    return [
        SlideData(
            number,
            "content",
            f"PT H{number}",
            f"PT B{number}",
            translation_en=(
                {"heading": f"EN H{number}", "body": f"EN B{number}"}
                if translated
                else None
            ),
        )
        for number in range(1, count + 1)
    ]


def _export(slide_paths: list[str] | None = None) -> AsyncMock:
    export = AsyncMock()
    export.export_slides = AsyncMock(
        return_value=_SLIDE_PATHS if slide_paths is None else slide_paths
    )
    return export


def _config(
    tmp_path: Path,
    *,
    language: str = LANGUAGE_PT,
    slides: list[SlideData] | None = None,
) -> BilingualExportConfig:
    pdf_builder = MagicMock()
    pdf_builder.build = MagicMock(return_value=_PDF_PATH)
    return BilingualExportConfig(
        project=_project(),
        slides_data=_slides(3) if slides is None else slides,
        pt_html=_HTML,
        output_dir=tmp_path,
        export=_export(),
        pdf_builder=pdf_builder,
        language=language,
        html_content=_HTML,
    )


@pytest.fixture
def prepare_assets() -> Iterator[MagicMock]:
    with patch(f"{_EXPORT}.prepare_carousel_export_assets") as mock_prepare:
        yield mock_prepare


@pytest.fixture
def export_logger() -> Iterator[MagicMock]:
    with patch(f"{_EXPORT}.logger") as mock_logger:
        yield mock_logger


@pytest.mark.unit
class TestRewriteAssetPathsDoubleQuotedUrl:
    """Scenario: double-quoted CSS url() references are rewritten."""

    def test_double_quoted_url_points_at_export_root(self) -> None:
        html = '<style>.bg{background:url("images/hero.jpg")}</style>'
        assert rewrite_asset_paths(html, "../") == (
            '<style>.bg{background:url("../images/hero.jpg")}</style>'
        )


@pytest.mark.unit
class TestRenderLanguageExportCalls:
    """Scenario: each language exports standard + HD with exact arguments."""

    async def test_standard_and_hd_exports_receive_exact_arguments(
        self, tmp_path: Path, prepare_assets: MagicMock
    ) -> None:
        config = _config(tmp_path)
        lang_dir = tmp_path / LANGUAGE_PT
        await render_language(config)
        assert config.export.export_slides.await_args_list == [
            call(
                html_content=_HTML,
                output_dir=str(lang_dir),
                config=ExportConfig(policy_version=_POLICY_VERSION, slide_count=3),
            ),
            call(
                html_content=_HTML,
                output_dir=str(lang_dir / HD_SUBDIR_NAME),
                config=ExportConfig(
                    hd=True, policy_version=_POLICY_VERSION, slide_count=3
                ),
            ),
        ]

    async def test_slide_count_falls_back_to_project_when_no_slides(
        self, tmp_path: Path, prepare_assets: MagicMock
    ) -> None:
        config = _config(tmp_path, slides=[])
        await render_language(config)
        for awaited in config.export.export_slides.await_args_list:
            assert awaited.kwargs["config"].slide_count == _PROJECT_SLIDE_COUNT

    async def test_creates_missing_output_parents(
        self, tmp_path: Path, prepare_assets: MagicMock
    ) -> None:
        output_dir = tmp_path / "nested" / "out"
        config = _config(output_dir)
        await render_language(config)
        assert (output_dir / LANGUAGE_PT / HD_SUBDIR_NAME).is_dir()

    async def test_existing_language_and_hd_dirs_are_reused(
        self, tmp_path: Path, prepare_assets: MagicMock, export_logger: MagicMock
    ) -> None:
        (tmp_path / LANGUAGE_PT / HD_SUBDIR_NAME).mkdir(parents=True)
        config = _config(tmp_path)
        await render_language(config)
        assert config.export.export_slides.await_count == 2
        export_logger.warning.assert_not_called()


@pytest.mark.unit
class TestRenderLanguageAssets:
    """Scenario: shared export assets are prepared once, on the PT pass."""

    async def test_pt_prepares_assets_for_output_dir(
        self, tmp_path: Path, prepare_assets: MagicMock
    ) -> None:
        await render_language(_config(tmp_path))
        prepare_assets.assert_called_once_with(tmp_path)

    async def test_en_does_not_prepare_assets(
        self, tmp_path: Path, prepare_assets: MagicMock
    ) -> None:
        await render_language(_config(tmp_path, language=LANGUAGE_EN))
        prepare_assets.assert_not_called()


@pytest.mark.unit
class TestRenderLanguageHdFailure:
    """Scenario: an HD export failure is logged and does not block the PDF."""

    async def test_hd_failure_logs_exact_warning(
        self, tmp_path: Path, prepare_assets: MagicMock, export_logger: MagicMock
    ) -> None:
        config = _config(tmp_path)
        config.export.export_slides = AsyncMock(
            side_effect=[_SLIDE_PATHS, RuntimeError("hd")]
        )
        await render_language(config)
        export_logger.warning.assert_called_once_with(
            _HD_FAILED_EVENT,
            project_id=str(config.project.id),
            language=LANGUAGE_PT,
            exc_info=True,
        )
        assert config.project.pdf_path == _PDF_PATH


@pytest.mark.unit
class TestRenderLanguagePdf:
    """Scenario: the PDF is built from the standard slides per language."""

    async def test_pdf_builder_receives_exact_arguments(
        self, tmp_path: Path, prepare_assets: MagicMock
    ) -> None:
        config = _config(tmp_path)
        await render_language(config)
        assert config.pdf_builder is not None
        build = config.pdf_builder.build
        assert isinstance(build, MagicMock)
        build.assert_called_once_with(
            slide_paths=_SLIDE_PATHS,
            output_dir=str(tmp_path / LANGUAGE_PT),
        )
        assert config.project.pdf_path == _PDF_PATH
        assert config.project.pdf_path_en is None

    async def test_en_pdf_path_is_stored_on_en_field(
        self, tmp_path: Path, prepare_assets: MagicMock
    ) -> None:
        config = _config(tmp_path, language=LANGUAGE_EN)
        await render_language(config)
        assert config.project.pdf_path_en == _PDF_PATH
        assert config.project.pdf_path is None

    async def test_no_pdf_builder_with_slides_skips_pdf(
        self, tmp_path: Path, prepare_assets: MagicMock
    ) -> None:
        config = _config(tmp_path)
        config.pdf_builder = None
        await render_language(config)
        assert config.project.pdf_path is None

    async def test_no_slide_paths_skips_pdf_builder(
        self, tmp_path: Path, prepare_assets: MagicMock
    ) -> None:
        config = _config(tmp_path)
        config.export = _export(slide_paths=[])
        await render_language(config)
        assert config.pdf_builder is not None
        build = config.pdf_builder.build
        assert isinstance(build, MagicMock)
        build.assert_not_called()

    async def test_pdf_failure_logs_exact_warning(
        self, tmp_path: Path, prepare_assets: MagicMock, export_logger: MagicMock
    ) -> None:
        config = _config(tmp_path)
        assert config.pdf_builder is not None
        config.pdf_builder.build = MagicMock(side_effect=OSError(_PDF_ERROR))
        await render_language(config)
        export_logger.warning.assert_called_once_with(
            _PDF_FAILED_EVENT,
            project_id=str(config.project.id),
            language=LANGUAGE_PT,
            error=_PDF_ERROR,
        )
        assert config.project.pdf_path is None


@pytest.mark.unit
class TestRunBilingualExportFanOut:
    """Scenario: PT always renders; EN renders from a redesigned EN deck."""

    def _base(self, tmp_path: Path, *, translated: bool) -> BilingualExportConfig:
        return BilingualExportConfig(
            project=_project(),
            slides_data=_slides(2, translated=translated),
            pt_html=_HTML,
            output_dir=tmp_path,
            export=_export(),
            pdf_builder=MagicMock(),
            template=MagicMock(),
            strategy_registry=MagicMock(),
            strategy_name="strategy-x",
        )

    def _expected(
        self, base: BilingualExportConfig, *, language: str, html: str
    ) -> BilingualExportConfig:
        return BilingualExportConfig(
            project=base.project,
            slides_data=base.slides_data,
            pt_html=base.pt_html,
            output_dir=base.output_dir,
            export=base.export,
            pdf_builder=base.pdf_builder,
            template=base.template,
            strategy_registry=base.strategy_registry,
            strategy_name=base.strategy_name,
            language=language,
            html_content=html,
        )

    async def test_pt_and_en_configs_carry_every_field(self, tmp_path: Path) -> None:
        base = self._base(tmp_path, translated=True)
        en_html = "<html>en</html>"
        with (
            patch(f"{_EXPORT}.render_language", new=AsyncMock()) as render,
            patch(f"{_EXPORT}.run_design", return_value=en_html) as design,
        ):
            await run_bilingual_export(base)
        assert render.await_args_list == [
            call(self._expected(base, language=LANGUAGE_PT, html=_HTML)),
            call(self._expected(base, language=LANGUAGE_EN, html=en_html)),
        ]
        design.assert_called_once_with(
            base.project,
            slides_data_for_language(base.slides_data, LANGUAGE_EN),
            template=base.template,
            language=LANGUAGE_EN,
            strategy_registry=base.strategy_registry,
            strategy_name=base.strategy_name,
        )

    async def test_untranslated_deck_renders_pt_only(self, tmp_path: Path) -> None:
        base = self._base(tmp_path, translated=False)
        with (
            patch(f"{_EXPORT}.render_language", new=AsyncMock()) as render,
            patch(f"{_EXPORT}.run_design") as design,
        ):
            await run_bilingual_export(base)
        assert render.await_args_list == [
            call(self._expected(base, language=LANGUAGE_PT, html=_HTML)),
        ]
        design.assert_not_called()
