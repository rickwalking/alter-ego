"""SEO analysis service for blog posts (QUAL-003)."""

from __future__ import annotations

from rag_backend.domain.constants.seo import (
    ISSUE_DESCRIPTION_TOO_LONG,
    ISSUE_DESCRIPTION_TOO_SHORT,
    ISSUE_MISSING_META_DESCRIPTION,
    ISSUE_MISSING_META_TITLE,
    ISSUE_NO_EXCERPT,
    ISSUE_NO_KEYWORDS,
    ISSUE_SLUG_TOO_LONG,
    ISSUE_TITLE_TOO_LONG,
    ISSUE_TITLE_TOO_SHORT,
    SEO_DESCRIPTION_IDEAL_MAX,
    SEO_DESCRIPTION_IDEAL_MIN,
    SEO_DESCRIPTION_MAX_LENGTH,
    SEO_DESCRIPTION_MIN_LENGTH,
    SEO_KEYWORD_MAX_COUNT,
    SEO_KEYWORD_MIN_COUNT,
    SEO_SCORE_PASS,
    SEO_SCORE_WARN,
    SEO_SLUG_MAX_LENGTH,
    SEO_TITLE_IDEAL_MAX,
    SEO_TITLE_IDEAL_MIN,
    SEO_TITLE_MAX_LENGTH,
    SEO_TITLE_MIN_LENGTH,
)


class SeoAnalysisService:
    """Analyzes blog post SEO readiness with actionable feedback."""

    def analyze(
        self,
        *,
        title: str,
        slug: str,
        meta_title: str | None,
        meta_description: str | None,
        excerpt: str | None,
        keywords: list[str],
    ) -> dict[str, object]:
        """Return SEO score, issues, and suggestions."""
        issues: list[dict[str, str]] = []
        score = 100
        score -= self._check_title(title, meta_title, issues)
        score -= self._check_description(meta_description, issues)
        score -= self._check_slug(slug, issues)
        score -= self._check_keywords(keywords, issues)
        score -= self._check_excerpt(excerpt, issues)

        final_score = max(0, score)
        return {
            "overall_score": final_score,
            "passed": final_score >= SEO_SCORE_PASS,
            "severity": self._severity(final_score),
            "issues": issues,
            "suggestions": [issue["message"] for issue in issues],
        }

    def _check_title(self, title: str, meta_title: str | None, issues: list[dict[str, str]]) -> int:
        penalty = 0
        effective_title = meta_title or title
        if not meta_title:
            issues.append(
                self._issue(ISSUE_MISSING_META_TITLE, "Add a meta title for search results")
            )
            penalty += 15
        elif len(effective_title) < SEO_TITLE_MIN_LENGTH:
            msg = f"Title is under {SEO_TITLE_MIN_LENGTH} characters"
            issues.append(self._issue(ISSUE_TITLE_TOO_SHORT, msg))
            penalty += 10
        elif len(effective_title) > SEO_TITLE_MAX_LENGTH:
            msg = f"Title exceeds {SEO_TITLE_MAX_LENGTH} characters"
            issues.append(self._issue(ISSUE_TITLE_TOO_LONG, msg))
            penalty += 10
        elif not (SEO_TITLE_IDEAL_MIN <= len(effective_title) <= SEO_TITLE_IDEAL_MAX):
            penalty += 5
        return penalty

    def _check_description(self, meta_description: str | None, issues: list[dict[str, str]]) -> int:
        penalty = 0
        if not meta_description:
            issues.append(self._issue(ISSUE_MISSING_META_DESCRIPTION, "Add a meta description"))
            penalty += 15
        elif len(meta_description) < SEO_DESCRIPTION_MIN_LENGTH:
            msg = f"Description is under {SEO_DESCRIPTION_MIN_LENGTH} chars"
            issues.append(self._issue(ISSUE_DESCRIPTION_TOO_SHORT, msg))
            penalty += 10
        elif len(meta_description) > SEO_DESCRIPTION_MAX_LENGTH:
            msg = f"Description exceeds {SEO_DESCRIPTION_MAX_LENGTH} chars"
            issues.append(self._issue(ISSUE_DESCRIPTION_TOO_LONG, msg))
            penalty += 10
        elif not (SEO_DESCRIPTION_IDEAL_MIN <= len(meta_description) <= SEO_DESCRIPTION_IDEAL_MAX):
            penalty += 5
        return penalty

    def _check_slug(self, slug: str, issues: list[dict[str, str]]) -> int:
        if len(slug) > SEO_SLUG_MAX_LENGTH:
            msg = f"Slug exceeds {SEO_SLUG_MAX_LENGTH} characters"
            issues.append(self._issue(ISSUE_SLUG_TOO_LONG, msg))
            return 5
        return 0

    def _check_keywords(self, keywords: list[str], issues: list[dict[str, str]]) -> int:
        if len(keywords) < SEO_KEYWORD_MIN_COUNT:
            issues.append(self._issue(ISSUE_NO_KEYWORDS, "Add at least one keyword"))
            return 10
        if len(keywords) > SEO_KEYWORD_MAX_COUNT:
            return 5
        return 0

    def _check_excerpt(self, excerpt: str | None, issues: list[dict[str, str]]) -> int:
        if not excerpt:
            issues.append(
                self._issue(ISSUE_NO_EXCERPT, "Add an excerpt for social sharing previews")
            )
            return 5
        return 0

    def _issue(self, code: str, message: str) -> dict[str, str]:
        return {"code": code, "message": message}

    def _severity(self, score: int) -> str:
        if score >= SEO_SCORE_PASS:
            return "pass"
        if score >= SEO_SCORE_WARN:
            return "warn"
        return "fail"


__all__ = ["SeoAnalysisService"]
