"""Unit tests for Phase 4 quality services."""

import pytest

from rag_backend.application.services.accessibility_check_service import AccessibilityCheckService
from rag_backend.application.services.ai_disclosure_service import AiDisclosureService
from rag_backend.application.services.plagiarism_detection_service import PlagiarismDetectionService
from rag_backend.application.services.seo_analysis_service import SeoAnalysisService
from rag_backend.domain.constants.ai_disclosure import (
    AI_ACTION_SUGGEST,
    AI_DISCLOSURE_ASSISTED,
    AI_DISCLOSURE_NONE,
)


class TestSeoAnalysisService:
    # Scenario: SEO analysis returns score and issues
    def test_analyze_flags_missing_meta(self) -> None:
        service = SeoAnalysisService()
        result = service.analyze(
            title="Short",
            slug="short",
            meta_title=None,
            meta_description=None,
            excerpt=None,
            keywords=[],
        )
        assert result["overall_score"] < 100
        assert result["passed"] is False
        assert len(result["issues"]) > 0

    def test_analyze_passes_well_optimized_post(self) -> None:
        service = SeoAnalysisService()
        result = service.analyze(
            title="The Real Cost of AI Security Breaches in 2026",
            slug="ai-security-breaches-2026",
            meta_title="AI Security Breaches Cost $4.2M — 2026 Report",
            meta_description=(
                "Explore the real financial impact of AI security breaches in 2026. "
                "Data from CISO surveys and breach reports."
            ),
            excerpt="A deep dive into breach costs.",
            keywords=["ai", "security"],
        )
        assert result["passed"] is True


class TestAccessibilityCheckService:
    # Scenario: Accessibility check detects missing alt text
    def test_missing_featured_alt(self) -> None:
        service = AccessibilityCheckService()
        result = service.check(
            content={"body": "Hello world"},
            featured_image_url="https://example.com/img.jpg",
        )
        assert result["passed"] is False
        assert any(i["code"] == "missing_alt_text" for i in result["issues"])

    def test_low_contrast_colors(self) -> None:
        service = AccessibilityCheckService()
        result = service.check(
            content={"body": "Text"},
            featured_image_url=None,
            design_colors={"text": "#cccccc", "background": "#ffffff"},
        )
        assert any(i["code"] == "low_contrast" for i in result["issues"])
        assert result["overall_score"] < 100

    def test_passes_with_alt_and_headings(self) -> None:
        service = AccessibilityCheckService()
        result = service.check(
            content={
                "body": "## Introduction\nContent here",
                "featured_image_alt": "Chart showing breach costs",
            },
            featured_image_url="https://example.com/img.jpg",
        )
        assert result["passed"] is True


class TestPlagiarismDetectionService:
    # Scenario: Plagiarism check compares against sources
    @pytest.mark.asyncio
    async def test_detects_high_overlap(self) -> None:
        service = PlagiarismDetectionService()
        content = "AI security breaches are becoming more frequent every year"
        sources = ["AI security breaches are becoming more frequent every year in enterprise"]
        result = await service.check(content, sources)
        assert result["overall_score"] < 85
        assert len(result["matches"]) >= 1

    @pytest.mark.asyncio
    async def test_original_content_passes(self) -> None:
        service = PlagiarismDetectionService()
        result = await service.check(
            "Completely original analysis of zero trust architecture",
            ["Unrelated source about cloud computing trends"],
        )
        assert result["passed"] is True


class TestAiDisclosureService:
    # Scenario: AI disclosure label reflects AI usage
    def test_none_without_actions(self) -> None:
        service = AiDisclosureService()
        assert service.compute_label({}) == AI_DISCLOSURE_NONE

    def test_assisted_after_suggest(self) -> None:
        service = AiDisclosureService()
        updated = service.record_action({}, AI_ACTION_SUGGEST)
        assert updated["ai_disclosure_label"] == AI_DISCLOSURE_ASSISTED
