"""Playwright-based carousel HTML to image export service with Neon Shell v2.0 support.

Implements the export techniques from docs/guides/carousel-export-techniques.md:
- Strategy A: Native 1080x1350 with CSS clamp overrides
- Strategy B: 2x Retina (2160x2700) with deviceScaleFactor
"""

from pathlib import Path

from playwright.async_api import async_playwright

from rag_backend.domain.constants import (
    CAROUSEL_HEIGHT,
    CAROUSEL_WIDTH,
    ENCODING_UTF8,
    IMAGE_FORMAT_JPEG,
    IMAGE_FORMAT_JPEG_LOWER,
    SLIDE_FILENAME_PREFIX,
    SLIDE_IMAGE_EXTENSION,
)
from rag_backend.domain.protocols import CarouselExportService, ExportConfig
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

DEFAULT_WIDTH = CAROUSEL_WIDTH
DEFAULT_HEIGHT = CAROUSEL_HEIGHT
DEFAULT_QUALITY = 100
HD_SCALE_FACTOR = 2

_VIEWPORT_WIDTH = 1400
_VIEWPORT_HEIGHT = 1800

_CROP_TARGET_WIDTH = CAROUSEL_WIDTH
_CROP_TARGET_HEIGHT = CAROUSEL_HEIGHT

# Base CSS injection for Strategy A (1080x1350)
_CSS_INJECTION_BASE = """
const style = document.createElement('style');
style.id = 'playwright-export-overrides';
style.textContent = `
  /* Widen feed to fit 1080px slides */
  .feed {
    max-width: none !important;
    width: 1150px !important;
    padding: 0 35px !important;
    margin: 0 auto !important;
  }
  /* Force exact slide dimensions */
  .ig-slide-inner {
    width: 1080px !important;
    height: 1350px !important;
    max-width: 1080px !important;
    max-height: 1350px !important;
    aspect-ratio: auto !important;
  }
  /* Scale fonts for 1080px canvas */
  .s1-title       { font-size: clamp(26px, 5.5vw, 56px) !important; }
  .slide-heading  { font-size: clamp(20px, 4.5vw, 50px) !important; }
  .body-p         { font-size: clamp(12px, 2.5vw, 30px) !important; }
  .s1-subtitle    { font-size: clamp(13px, 2.5vw, 28px) !important; }
  .s1-tldr        { font-size: clamp(11px, 2.2vw, 24px) !important; }
  .cta-title      { font-size: clamp(20px, 4.5vw, 52px) !important; }
  .cta-body       { font-size: clamp(12px, 2.4vw, 30px) !important; }
  .feature-title  { font-size: clamp(11px, 2.2vw, 28px) !important; }
  .feature-body   { font-size: clamp(10px, 2vw, 24px) !important; }
  .stat-number    { font-size: clamp(18px, 4vw, 42px) !important; }
  .insight-card   { font-size: clamp(11px, 2.2vw, 26px) !important; }
  /* Adjust padding for larger canvas */
  .slide-content  { padding: 52px 40px 44px !important; }
  .slide-1-content { padding: 44px 40px 68px !important; }
  /* Larger watermark for export */
  .creator-watermark       { padding: 10px 18px 10px 10px !important; gap: 12px !important; }
  .creator-watermark-avatar { width: 36px !important; height: 36px !important; border-width: 2px !important; }
  .creator-watermark-name  { font-size: 14px !important; max-width: 160px !important; }
  .creator-watermark-handle { font-size: 12px !important; max-width: 160px !important; }
`;
document.head.appendChild(style);
"""

# HD CSS injection for Strategy B (2160x2700)
_CSS_INJECTION_HD = """
const style = document.createElement('style');
style.id = 'playwright-export-overrides-hd';
style.textContent = `
  .feed {
    max-width: none !important;
    width: 2300px !important;
    padding: 0 70px !important;
    margin: 0 auto !important;
  }
  .ig-slide-inner {
    width: 2160px !important;
    height: 2700px !important;
    max-width: 2160px !important;
    max-height: 2700px !important;
    aspect-ratio: auto !important;
  }
  .s1-title       { font-size: clamp(52px, 5.5vw, 112px) !important; }
  .slide-heading  { font-size: clamp(40px, 4.5vw, 100px) !important; }
  .body-p         { font-size: clamp(24px, 2.5vw, 60px) !important; }
  .s1-subtitle    { font-size: clamp(26px, 2.5vw, 56px) !important; }
  .s1-tldr        { font-size: clamp(22px, 2.2vw, 48px) !important; }
  .cta-title      { font-size: clamp(40px, 4.5vw, 104px) !important; }
  .cta-body       { font-size: clamp(24px, 2.4vw, 60px) !important; }
  .feature-title  { font-size: clamp(22px, 2.2vw, 56px) !important; }
  .feature-body   { font-size: clamp(20px, 2vw, 48px) !important; }
  .stat-number    { font-size: clamp(36px, 4vw, 84px) !important; }
  .insight-card   { font-size: clamp(22px, 2.2vw, 52px) !important; }
  .slide-content  { padding: 104px 80px 88px !important; }
  .slide-1-content { padding: 88px 80px 136px !important; }
  .creator-watermark       { padding: 14px 24px 14px 14px !important; gap: 16px !important; }
  .creator-watermark-avatar { width: 48px !important; height: 48px !important; border-width: 3px !important; }
  .creator-watermark-name  { font-size: 20px !important; max-width: 200px !important; }
  .creator-watermark-handle { font-size: 14px !important; max-width: 200px !important; }
`;
document.head.appendChild(style);
"""


def _crop_border_artifact(path: str, target_width: int, target_height: int) -> None:
    """Crop 1px border artifact from exported slide image."""
    try:
        from PIL import Image as PILImage

        with PILImage.open(path) as img:
            w, h = img.size
            if w == target_width and h == target_height:
                return
            crop_box = (
                (w - target_width) // 2,
                (h - target_height) // 2,
                (w - target_width) // 2 + target_width,
                (h - target_height) // 2 + target_height,
            )
            cropped = img.crop(crop_box)
            cropped.save(path, IMAGE_FORMAT_JPEG, quality=DEFAULT_QUALITY)
    except Exception:
        logger.warning(
            "crop_border_artifact_failed",
            path=path,
            target_width=target_width,
            target_height=target_height,
        )


class PlaywrightExportService(CarouselExportService):
    """Playwright implementation for exporting carousel HTML to images.

    Supports CSS injection for font clamp overrides, HD (2x) retina
    export, and 1px border artifact cropping per the export guide.
    """

    async def export_slides(
        self,
        html_content: str,
        output_dir: str,
        config: ExportConfig | None = None,
    ) -> list[str]:
        """Render HTML carousel and export individual slide images.

        Args:
            html_content: Self-contained HTML carousel string.
            output_dir: Directory for output files.
            config: Optional export configuration overrides.

        Returns:
            List of paths to exported slide images.
        """
        cfg = config or ExportConfig()
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        html_file = output_path / "carousel.html"
        html_file.write_text(html_content, encoding=ENCODING_UTF8)

        exported_paths: list[str] = []
        scale = HD_SCALE_FACTOR if cfg.hd else 1
        target_width = cfg.width * scale
        target_height = cfg.height * scale
        injection = _CSS_INJECTION_HD if cfg.hd else _CSS_INJECTION_BASE

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(
                viewport={
                    "width": _VIEWPORT_WIDTH * scale,
                    "height": _VIEWPORT_HEIGHT * scale,
                },
                device_scale_factor=scale,
            )

            file_url = f"file://{html_file.absolute()}"
            await page.goto(file_url)
            await page.wait_for_timeout(4000)

            # Inject default + optional CSS overrides
            await page.evaluate(injection)
            if cfg.css_overrides:
                import json

                safe_css = json.dumps(cfg.css_overrides)
                override_js = (
                    "const s = document.createElement('style');"
                    f"s.textContent = {safe_css};"
                    "document.head.appendChild(s);"
                )
                await page.evaluate(override_js)

            # Screenshot each .ig-slide-inner element
            slide_inners = await page.locator(".ig-slide-inner").all()
            if not slide_inners:
                # Fallback to legacy .slide selector
                slide_inners = await page.locator(".slide").all()

            for i, slide in enumerate(slide_inners, 1):
                filename = f"{SLIDE_FILENAME_PREFIX}{i}{SLIDE_IMAGE_EXTENSION}"
                slide_path = str(output_path / filename)
                await slide.screenshot(
                    path=slide_path,
                    type=IMAGE_FORMAT_JPEG_LOWER,
                    quality=cfg.quality,
                )
                # Crop 1px border artifact
                _crop_border_artifact(
                    slide_path,
                    target_width,
                    target_height,
                )
                exported_paths.append(slide_path)

            await browser.close()

        return exported_paths
