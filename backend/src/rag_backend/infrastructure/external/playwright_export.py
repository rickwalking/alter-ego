"""Playwright-based carousel HTML to image export service with Neon Shell v2.0 support.

Implements the export techniques from docs/guides/carousel-export-techniques.md:
- Strategy A: Native 1080x1350 with CSS clamp overrides
- Strategy B: 2x Retina (2160x2700) with deviceScaleFactor
"""

from pathlib import Path

from playwright.async_api import async_playwright

from rag_backend.application.services.carousel.presentation_policy import (
    load_presentation_policy,
)
from rag_backend.domain.constants import (
    CAROUSEL_HEIGHT,
    CAROUSEL_WIDTH,
    ENCODING_UTF8,
    IMAGE_FORMAT_JPEG,
    IMAGE_FORMAT_JPEG_LOWER,
    SLIDE_FILENAME_PREFIX,
    SLIDE_IMAGE_EXTENSION,
)
from rag_backend.domain.constants.carousel_presentation import (
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.constants.playwright_geometry import (
    ERR_SCREENSHOT_DIMENSION_MISMATCH,
)
from rag_backend.domain.protocols import CarouselExportService, ExportConfig
from rag_backend.infrastructure.external.playwright_geometry import (
    PlaywrightExportPreflightError,
    run_export_preflight,
)
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
  .slide-heading  { font-size: clamp(23px, 4.8vw, 56px) !important; }
  .body-p         { font-size: clamp(13px, 2.7vw, 34px) !important; }
  .s1-subtitle    { font-size: clamp(14px, 2.7vw, 32px) !important; }
  .s1-tldr        { font-size: clamp(12px, 2.3vw, 28px) !important; }
  .s1-swipe       { font-size: 26px !important; }
  .slide-number,
  .slide-hero-number { font-size: 26px !important; margin-bottom: 14px !important; }
  .counter-label  { font-size: 22px !important; }
  .counter-dot    { width: 14px !important; height: 14px !important; }
  .counter-dot.active { width: 42px !important; border-radius: 7px !important; }
  .slide-hero-heading { font-size: clamp(29px, 5.8vw, 64px) !important; }
  .slide-hero-body    { font-size: clamp(13px, 2.45vw, 28px) !important; line-height: 1.52 !important; }
  .closing-card   { width: min(100%, 720px) !important; padding: 48px 54px 56px !important; border-radius: 30px !important; }
  .closing-avatar { width: 168px !important; height: 168px !important; border-width: 4px !important; margin-bottom: 28px !important; }
  .closing-name   { font-size: clamp(36px, 5.5vw, 64px) !important; }
  .closing-cta    { font-size: clamp(15px, 2.2vw, 26px) !important; }
  .closing-handle { font-size: clamp(18px, 2.4vw, 30px) !important; }
  .closing-website { font-size: clamp(18px, 2.5vw, 30px) !important; padding: 18px 42px !important; }
  .cta-title      { font-size: clamp(20px, 4.5vw, 52px) !important; }
  .cta-body       { font-size: clamp(12px, 2.4vw, 30px) !important; }
  .feature-title  { font-size: clamp(11px, 2.2vw, 28px) !important; }
  .feature-body   { font-size: clamp(10px, 2vw, 24px) !important; }
  .summary-title  { font-size: clamp(11px, 2.2vw, 28px) !important; }
  .summary-body   { font-size: clamp(10px, 2vw, 24px) !important; }
  .summary-item .summary-icon { width: 32px !important; height: 32px !important; }
  .summary-item .summary-icon svg { width: 24px !important; height: 24px !important; }
  .stat-number    { font-size: clamp(18px, 4vw, 42px) !important; }
  .insight-card   { font-size: clamp(11px, 2.2vw, 26px) !important; }
  /* Adjust padding for larger canvas */
  .slide-content      { padding: 52px 40px 44px !important; }
  .slide-1-content    { padding: 44px 40px 68px !important; }
  .slide-hero-content { padding: 44px 40px 160px !important; }
  .slide-presentation { padding: 44px 40px 160px !important; }
  .slide-hero-main,
  .slide-presentation-copy { max-height: calc(100% - 190px) !important; }
  /* Larger watermark for export */
  .creator-watermark       { padding: 16px 28px 16px 16px !important; gap: 18px !important; }
  .creator-watermark-avatar { width: 72px !important; height: 72px !important; border-width: 3px !important; }
  .creator-watermark-name  { font-size: 24px !important; max-width: 260px !important; }
  .creator-watermark-handle { font-size: 18px !important; max-width: 260px !important; }
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
  .s1-title       { font-size: clamp(58px, 5.8vw, 126px) !important; }
  .slide-heading  { font-size: clamp(46px, 4.8vw, 112px) !important; }
  .body-p         { font-size: clamp(26px, 2.7vw, 68px) !important; }
  .s1-subtitle    { font-size: clamp(28px, 2.7vw, 64px) !important; }
  .s1-tldr        { font-size: clamp(24px, 2.3vw, 56px) !important; }
  .s1-swipe       { font-size: 52px !important; }
  .slide-number,
  .slide-hero-number { font-size: 52px !important; margin-bottom: 28px !important; }
  .counter-label  { font-size: 44px !important; }
  .counter-dot    { width: 28px !important; height: 28px !important; }
  .counter-dot.active { width: 84px !important; border-radius: 14px !important; }
  .slide-hero-heading { font-size: clamp(58px, 5.8vw, 126px) !important; }
  .slide-hero-body    { font-size: clamp(26px, 2.45vw, 56px) !important; line-height: 1.52 !important; }
  .closing-card   { width: min(100%, 1440px) !important; padding: 96px 108px 112px !important; border-radius: 60px !important; }
  .closing-avatar { width: 336px !important; height: 336px !important; border-width: 8px !important; margin-bottom: 56px !important; }
  .closing-name   { font-size: clamp(72px, 5.5vw, 128px) !important; }
  .closing-cta    { font-size: clamp(30px, 2.2vw, 52px) !important; }
  .closing-handle { font-size: clamp(36px, 2.4vw, 60px) !important; }
  .closing-website { font-size: clamp(36px, 2.5vw, 60px) !important; padding: 36px 84px !important; }
  .cta-title      { font-size: clamp(40px, 4.5vw, 104px) !important; }
  .cta-body       { font-size: clamp(24px, 2.4vw, 60px) !important; }
  .feature-title  { font-size: clamp(22px, 2.2vw, 56px) !important; }
  .feature-body   { font-size: clamp(20px, 2vw, 48px) !important; }
  .summary-title  { font-size: clamp(22px, 2.2vw, 56px) !important; }
  .summary-body   { font-size: clamp(20px, 2vw, 48px) !important; }
  .summary-item .summary-icon { width: 64px !important; height: 64px !important; }
  .summary-item .summary-icon svg { width: 48px !important; height: 48px !important; }
  .stat-number    { font-size: clamp(36px, 4vw, 84px) !important; }
  .insight-card   { font-size: clamp(22px, 2.2vw, 52px) !important; }
  .slide-content      { padding: 104px 80px 88px !important; }
  .slide-1-content    { padding: 88px 80px 136px !important; }
  .slide-hero-content { padding: 88px 80px 320px !important; }
  .slide-presentation { padding: 88px 80px 320px !important; }
  .slide-hero-main,
  .slide-presentation-copy { max-height: calc(100% - 380px) !important; }
  .creator-watermark       { padding: 32px 56px 32px 32px !important; gap: 36px !important; }
  .creator-watermark-avatar { width: 144px !important; height: 144px !important; border-width: 6px !important; }
  .creator-watermark-name  { font-size: 48px !important; max-width: 520px !important; }
  .creator-watermark-handle { font-size: 36px !important; max-width: 520px !important; }
`;
document.head.appendChild(style);
"""


_BORDER_ARTIFACT_MAX_PX = 5


def _crop_border_artifact(path: str, target_width: int, target_height: int) -> None:
    """Crop small border artifacts (up to 5px) from exported slide image edges.

    Uses an exact target box so odd-pixel excess is removed symmetrically.
    Mismatches beyond the tolerated border artifact raise export errors.
    """
    try:
        from PIL import Image as PILImage

        with PILImage.open(path) as img:
            width, height = img.size
    except Exception:
        logger.warning(
            "crop_border_artifact_failed",
            path=path,
            target_width=target_width,
            target_height=target_height,
        )
        return

    if width == target_width and height == target_height:
        return

    delta_width = width - target_width
    delta_height = height - target_height
    if (
        abs(delta_width) > _BORDER_ARTIFACT_MAX_PX
        or abs(delta_height) > _BORDER_ARTIFACT_MAX_PX
    ):
        raise PlaywrightExportPreflightError(
            ERR_SCREENSHOT_DIMENSION_MISMATCH,
        )

    left = max(0, (width - target_width) // 2)
    top = max(0, (height - target_height) // 2)
    crop_box = (
        left,
        top,
        left + target_width,
        top + target_height,
    )

    try:
        from PIL import Image as PILImage

        with PILImage.open(path) as img:
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

    Supports CSS injection for font clamp overrides and HD (2x) retina
    export via deviceScaleFactor with CSS-pixel screenshots.
    """

    @staticmethod
    async def export_slides(
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

            policy = load_presentation_policy(DEFAULT_PRESENTATION_POLICY_VERSION)
            await run_export_preflight(page, policy, hd=cfg.hd)

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
                    scale="css",
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
