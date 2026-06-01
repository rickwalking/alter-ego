"""Application-layer carousel export tool for pipeline."""

from rag_backend.domain.protocols import CarouselExportService


class CarouselExportTool:
    """Application tool wrapping the CarouselExportService protocol.

    Provides a simplified interface for the carousel agent to export
    HTML carousel content to individual slide images.
    """

    DEFAULT_WIDTH = 1080
    DEFAULT_HEIGHT = 1350
    DEFAULT_QUALITY = 95

    def __init__(self, export_service: CarouselExportService) -> None:
        self._service = export_service

    async def export_carousel(
        self,
        html_content: str,
        output_dir: str,
        *,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        css_overrides: str | None = None,
        quality: int = DEFAULT_QUALITY,
        hd: bool = False,
    ) -> list[str]:
        """Export HTML carousel to individual slide images.

        Args:
            html_content: Self-contained HTML carousel content.
            output_dir: Directory for output files.
            width: Slide width in pixels (default 1080).
            height: Slide height in pixels (default 1350).
            css_overrides: Optional extra CSS injected at export time.
            quality: JPEG quality (default 95).
            hd: Export at 2x resolution (2160x2700).

        Returns:
            List of paths to exported slide images.
        """
        return await self._service.export_slides(
            html_content=html_content,
            output_dir=output_dir,
            width=width,
            height=height,
            css_overrides=css_overrides,
            quality=quality,
            hd=hd,
        )
