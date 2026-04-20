"""Application-layer image generation tool for carousel pipeline."""

from rag_backend.domain.protocols import ImageGenerationService


class ImageGenerationTool:
    """Application tool wrapping the ImageGenerationService protocol.

    Provides a simplified interface for the carousel agent to generate
    images for content-heavy slides with rate limiting.
    """

    IMAGE_GENERATION_DELAY_SECONDS = 2.5

    def __init__(self, image_service: ImageGenerationService) -> None:
        self._service = image_service

    async def generate_content_images(
        self,
        prompts: list[tuple[int, str]],
        output_dir: str,
    ) -> dict[int, str]:
        """Generate images for content slides with rate limiting.

        Args:
            prompts: List of (slide_number, prompt) tuples.
            output_dir: Directory to save generated images.

        Returns:
            Dict mapping slide_number to output file path.
        """
        import asyncio
        from pathlib import Path

        images_dir = Path(output_dir) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        results: dict[int, str] = {}
        for slide_number, prompt in prompts:
            output_path = str(images_dir / f"slide_{slide_number}.jpg")
            await self._service.generate_image(
                prompt=prompt,
                output_path=output_path,
            )
            results[slide_number] = output_path
            await asyncio.sleep(self.IMAGE_GENERATION_DELAY_SECONDS)

        return results
