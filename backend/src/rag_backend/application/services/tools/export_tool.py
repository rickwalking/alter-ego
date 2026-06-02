"""Application-layer carousel export tool for pipeline."""

from rag_backend.domain.protocols import CarouselExportService, ExportConfig


class CarouselExportTool:
    """Application tool wrapping the CarouselExportService protocol.

    Provides a simplified interface for the carousel agent to export
    HTML carousel content to individual slide images.
    """

    def __init__(self, export_service: CarouselExportService) -> None:
        self._service = export_service

    async def export_carousel(
        self,
        html_content: str,
        output_dir: str,
        config: ExportConfig | None = None,
    ) -> list[str]:
        """Export HTML carousel to individual slide images.

        Args:
            html_content: Self-contained HTML carousel content.
            output_dir: Directory for output files.
            config: Optional export configuration overrides.

        Returns:
            List of paths to exported slide images.
        """
        return await self._service.export_slides(
            html_content=html_content,
            output_dir=output_dir,
            config=config or ExportConfig(),
        )
