"""Unit tests for ImageGenerationTool and CarouselExportTool."""

import pathlib

import pytest

from rag_backend.application.services.tools.export_tool import CarouselExportTool
from rag_backend.application.services.tools.image_tool import ImageGenerationTool
from rag_backend.domain.protocols import ExportConfig


@pytest.mark.unit
class TestImageGenerationTool:
    """Tests for ImageGenerationTool."""

    async def test_generate_content_images_creates_output(self, tmp_path):
        """Should generate images and return slide-to-path mapping."""
        from unittest.mock import AsyncMock

        mock_service = AsyncMock()
        mock_service.generate_image = AsyncMock(return_value="/output/image.jpg")

        tool = ImageGenerationTool(image_service=mock_service)

        prompts = [
            (2, "A neural network comic style"),
            (3, "Data visualization manga style"),
        ]

        results = await tool.generate_content_images(
            prompts=prompts,
            output_dir=str(tmp_path),
        )

        assert 2 in results
        assert 3 in results
        assert mock_service.generate_image.call_count == 2

    async def test_generate_content_images_rate_limit_delay(self, tmp_path):
        """Should add delay between image generation calls."""
        import time
        from unittest.mock import AsyncMock

        mock_service = AsyncMock()
        mock_service.generate_image = AsyncMock(return_value="/output/image.jpg")

        tool = ImageGenerationTool(image_service=mock_service)
        tool.IMAGE_GENERATION_DELAY_SECONDS = 0.1

        prompts = [(1, "prompt 1"), (2, "prompt 2")]

        start = time.time()
        await tool.generate_content_images(
            prompts=prompts,
            output_dir=str(tmp_path),
        )
        elapsed = time.time() - start

        assert elapsed >= 0.1

    async def test_generate_content_images_empty_prompts(self, tmp_path):
        """Should return empty dict when no prompts provided."""
        from unittest.mock import AsyncMock

        mock_service = AsyncMock()
        mock_service.generate_image = AsyncMock(return_value="/output/image.jpg")

        tool = ImageGenerationTool(image_service=mock_service)

        results = await tool.generate_content_images(
            prompts=[],
            output_dir=str(tmp_path),
        )

        assert results == {}
        assert mock_service.generate_image.call_count == 0

    async def test_generate_content_images_creates_images_dir(self, tmp_path):
        """Should create the images subdirectory."""
        from unittest.mock import AsyncMock

        mock_service = AsyncMock()
        mock_service.generate_image = AsyncMock(return_value="/output/image.jpg")

        tool = ImageGenerationTool(image_service=mock_service)

        output_dir = str(tmp_path / "carousel_output")
        prompts = [(1, "test prompt")]

        await tool.generate_content_images(
            prompts=prompts,
            output_dir=output_dir,
        )

        assert (pathlib.Path(output_dir) / "images").is_dir()


@pytest.mark.unit
class TestCarouselExportTool:
    """Tests for CarouselExportTool."""

    async def test_export_carousel_delegates_to_service(self):
        """Should delegate export to the underlying service."""
        from unittest.mock import AsyncMock

        mock_service = AsyncMock()
        mock_service.export_slides = AsyncMock(
            return_value=["/output/slide_1.jpg", "/output/slide_2.jpg"]
        )

        tool = CarouselExportTool(export_service=mock_service)

        result = await tool.export_carousel(
            html_content="<html>test</html>",
            output_dir="/output",
        )

        assert len(result) == 2
        mock_service.export_slides.assert_called_once_with(
            html_content="<html>test</html>",
            output_dir="/output",
            config=ExportConfig(),
        )

    async def test_export_carousel_custom_dimensions(self):
        """Should pass custom dimensions to the service."""
        from unittest.mock import AsyncMock

        mock_service = AsyncMock()
        mock_service.export_slides = AsyncMock(return_value=[])

        tool = CarouselExportTool(export_service=mock_service)

        await tool.export_carousel(
            html_content="<html>test</html>",
            output_dir="/output",
            config=ExportConfig(width=1920, height=1080),
        )

        mock_service.export_slides.assert_called_once_with(
            html_content="<html>test</html>",
            output_dir="/output",
            config=ExportConfig(width=1920, height=1080),
        )

    async def test_export_defaults(self):
        """Should have correct default dimensions."""
        assert ExportConfig().width == 1080
        assert ExportConfig().height == 1350
        assert ExportConfig().quality == 95
