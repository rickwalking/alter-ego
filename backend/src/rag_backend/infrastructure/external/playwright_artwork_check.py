"""Export preflight: every slide artwork the HTML references exists.

Runs before Playwright opens the page. A missing ``images/slide_N.jpg`` makes
``img.decode()`` reject, which the decode step reports as the misleading
``image_decode_timeout``; this check names the slide instead.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from rag_backend.domain.constants.playwright_geometry import (
    ERR_EXPORT_PREFLIGHT_FAILED,
    PREFLIGHT_SCALE_HD,
    PREFLIGHT_SCALE_STANDARD,
    VIOLATION_SLIDE_ARTWORK_MISSING,
)
from rag_backend.infrastructure.external.playwright_geometry import (
    GeometryViolation,
    PlaywrightExportPreflightError,
    PreflightReport,
)
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

_SLIDE_MARKER = 'class="ig-slide-inner"'
_ARTWORK_IMG = re.compile(
    r'<div class="slide-artwork(?:\s[^"]*)?">\s*<img src="(?P<src>[^"]+)"'
)
_SLIDE_LABEL = "slide_{}"


def _is_local(src: str) -> bool:
    return not urlparse(src).scheme


def missing_artwork_violations(
    html_content: str, base_dir: Path
) -> tuple[GeometryViolation, ...]:
    """One violation per slide whose local artwork file does not exist."""
    violations: list[GeometryViolation] = []
    chunks = html_content.split(_SLIDE_MARKER)[1:]
    for slide_number, chunk in enumerate(chunks, 1):
        match = _ARTWORK_IMG.search(chunk)
        if match is None or not _is_local(match["src"]):
            continue
        if (base_dir / unquote(match["src"])).is_file():
            continue
        label = _SLIDE_LABEL.format(slide_number)
        violations.append(
            GeometryViolation(
                code=VIOLATION_SLIDE_ARTWORK_MISSING,
                slide_number=slide_number,
                message=f"{VIOLATION_SLIDE_ARTWORK_MISSING}: {label} ({match['src']})",
                blocking=True,
            )
        )
    return tuple(violations)


def ensure_artwork_files(
    html_content: str, base_dir: Path, *, hd: bool = False
) -> None:
    """Raise a preflight error naming every slide whose artwork is missing."""
    violations = missing_artwork_violations(html_content, base_dir)
    if not violations:
        return
    scale = PREFLIGHT_SCALE_HD if hd else PREFLIGHT_SCALE_STANDARD
    labels = ", ".join(_SLIDE_LABEL.format(v.slide_number) for v in violations)
    reason = f"{VIOLATION_SLIDE_ARTWORK_MISSING}: {labels}"
    logger.warning(
        "export_preflight_failed",
        scale=scale,
        violation_codes=[v.code for v in violations],
        reason=reason,
    )
    message = f"{ERR_EXPORT_PREFLIGHT_FAILED}: {reason}"
    raise PlaywrightExportPreflightError(
        message,
        report=PreflightReport(
            passed=False,
            scale=scale,
            geometry_skipped=True,
            slide_reports=(),
            image_reports=(),
            violations=violations,
            warnings=(),
        ),
    )


__all__ = ["ensure_artwork_files", "missing_artwork_violations"]
