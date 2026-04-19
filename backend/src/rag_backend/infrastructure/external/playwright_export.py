"""Playwright-based carousel HTML to image export service."""

from pathlib import Path

from playwright.async_api import async_playwright

from rag_backend.domain.protocols import CarouselExportService


class PlaywrightExportService(CarouselExportService):
    """Playwright implementation for exporting carousel HTML to images."""

    async def export_slides(
        self,
        html_content: str,
        output_dir: str,
        width: int = 1080,
        height: int = 1350,
    ) -> list[str]:
        """Render HTML carousel and export individual slide images.

        Returns list of paths to exported slide images.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Write HTML to temp file
        html_file = output_path / "carousel.html"
        html_file.write_text(html_content, encoding="utf-8")

        exported_paths: list[str] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=1,
            )

            file_url = f"file://{html_file.absolute()}"
            await page.goto(file_url)
            await page.wait_for_timeout(4000)

            slides = await page.locator(".slide").all()
            for i, slide in enumerate(slides, 1):
                slide_path = str(output_path / f"slide_{i}.jpg")
                await slide.screenshot(
                    path=slide_path,
                    type="jpeg",
                    quality=95,
                )
                exported_paths.append(slide_path)

            await browser.close()

        return exported_paths
