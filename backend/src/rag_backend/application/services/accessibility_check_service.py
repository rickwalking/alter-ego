"""Accessibility check service for blog content (QUAL-004)."""

from __future__ import annotations

from rag_backend.domain.constants.accessibility import (
    A11Y_ISSUE_EMPTY_ALT,
    A11Y_ISSUE_LOW_CONTRAST,
    A11Y_ISSUE_MISSING_ALT,
    A11Y_ISSUE_NO_HEADINGS,
    A11Y_SCORE_PASS,
    A11Y_SCORE_WARN,
    A11Y_SEVERITY_ERROR,
    A11Y_SEVERITY_INFO,
    A11Y_SEVERITY_WARNING,
    HEX_COLOR_LENGTH,
    SRGB_THRESHOLD,
    WCAG_AA_CONTRAST_NORMAL,
)


class AccessibilityCheckService:
    """Checks blog content for accessibility issues."""

    def check(
        self,
        *,
        content: dict[str, object],
        featured_image_url: str | None,
        design_colors: dict[str, str] | None = None,
    ) -> dict[str, object]:
        """Analyze content and return accessibility score with warnings."""
        issues: list[dict[str, str]] = []
        score = 100

        body = str(content.get("body", "")) if isinstance(content, dict) else ""
        images = content.get("images", []) if isinstance(content, dict) else []
        if not isinstance(images, list):
            images = []

        if featured_image_url and not self._has_alt_for_featured(content):
            issues.append(
                self._issue(
                    A11Y_ISSUE_MISSING_ALT,
                    "Featured image is missing alt text",
                    A11Y_SEVERITY_ERROR,
                )
            )
            score -= 20

        for idx, image in enumerate(images):
            if not isinstance(image, dict):
                continue
            alt = image.get("alt")
            if alt is None:
                issues.append(
                    self._issue(
                        A11Y_ISSUE_MISSING_ALT,
                        f"Image {idx + 1} is missing alt text",
                        A11Y_SEVERITY_ERROR,
                    )
                )
                score -= 15
            elif not str(alt).strip():
                issues.append(
                    self._issue(
                        A11Y_ISSUE_EMPTY_ALT,
                        f"Image {idx + 1} has empty alt text",
                        A11Y_SEVERITY_WARNING,
                    )
                )
                score -= 10

        if body and not self._has_headings(body):
            issues.append(
                self._issue(
                    A11Y_ISSUE_NO_HEADINGS,
                    "Content has no heading structure — add H2/H3 headings",
                    A11Y_SEVERITY_INFO,
                )
            )
            score -= 5

        if design_colors:
            contrast_issues = self._check_color_contrast(design_colors)
            issues.extend(contrast_issues)
            score -= len(contrast_issues) * 10

        final_score = max(0, score)
        return {
            "overall_score": final_score,
            "passed": final_score >= A11Y_SCORE_PASS,
            "severity": self._severity(final_score),
            "issues": issues,
        }

    def _has_alt_for_featured(self, content: dict[str, object]) -> bool:
        alt = content.get("featured_image_alt")
        return isinstance(alt, str) and bool(alt.strip())

    def _has_headings(self, body: str) -> bool:
        lines = body.split("\n")
        return any(line.startswith("#") for line in lines)

    def _check_color_contrast(self, colors: dict[str, str]) -> list[dict[str, str]]:
        issues: list[dict[str, str]] = []
        fg = colors.get("text", colors.get("foreground", ""))
        bg = colors.get("background", colors.get("bg", ""))
        if not fg or not bg:
            return issues
        ratio = self._contrast_ratio(fg, bg)
        if ratio < WCAG_AA_CONTRAST_NORMAL:
            msg = (
                f"Text/background contrast ratio {ratio:.1f}:1 is below "
                f"WCAG AA ({WCAG_AA_CONTRAST_NORMAL}:1)"
            )
            issues.append(self._issue(A11Y_ISSUE_LOW_CONTRAST, msg, A11Y_SEVERITY_ERROR))
        return issues

    def _contrast_ratio(self, fg_hex: str, bg_hex: str) -> float:
        fg_lum = self._relative_luminance(fg_hex)
        bg_lum = self._relative_luminance(bg_hex)
        lighter = max(fg_lum, bg_lum)
        darker = min(fg_lum, bg_lum)
        return (lighter + 0.05) / (darker + 0.05)

    def _relative_luminance(self, hex_color: str) -> float:
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != HEX_COLOR_LENGTH:
            return 0.5
        r = int(hex_color[0:2], 16) / 255
        g = int(hex_color[2:4], 16) / 255
        b = int(hex_color[4:6], 16) / 255

        def channel(c: float) -> float:
            return c / 12.92 if c <= SRGB_THRESHOLD else ((c + 0.055) / 1.055) ** 2.4

        return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

    def _issue(self, code: str, message: str, severity: str) -> dict[str, str]:
        return {"code": code, "message": message, "severity": severity}

    def _severity(self, score: int) -> str:
        if score >= A11Y_SCORE_PASS:
            return "pass"
        if score >= A11Y_SCORE_WARN:
            return "warn"
        return "fail"


__all__ = ["AccessibilityCheckService"]
