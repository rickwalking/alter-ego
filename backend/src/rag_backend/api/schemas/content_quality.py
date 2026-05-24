"""Pydantic schemas for content quality endpoints (Phase 4)."""

from pydantic import BaseModel, Field


class PlagiarismCheckResponse(BaseModel):
    """Response from plagiarism detection."""

    overall_score: float
    passed: bool
    severity: str
    matches: list[dict[str, object]] = Field(default_factory=list)


class SeoAnalysisResponse(BaseModel):
    """Response from SEO analysis."""

    overall_score: int
    passed: bool
    severity: str
    issues: list[dict[str, str]] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class AccessibilityCheckResponse(BaseModel):
    """Response from accessibility check."""

    overall_score: int
    passed: bool
    severity: str
    issues: list[dict[str, str]] = Field(default_factory=list)


class AiDisclosureResponse(BaseModel):
    """AI disclosure label for content."""

    label: str
    requires_disclosure: bool
    ai_action_count: int = 0


class EditorialAnalyticsSummary(BaseModel):
    """Dashboard analytics summary."""

    total_posts: int
    published_this_week: int
    published_this_month: int
    content_velocity_per_week: int
    status_breakdown: dict[str, int]
    average_views: int
    pending_review: int
    draft_count: int
    quality_score_average: float


class EditorialVelocityWeek(BaseModel):
    """Weekly publish count bucket."""

    week_start: str
    published_count: int


class EditorialAnalyticsResponse(BaseModel):
    """Full analytics response."""

    summary: EditorialAnalyticsSummary
    velocity_by_week: list[EditorialVelocityWeek]


__all__ = [
    "AccessibilityCheckResponse",
    "AiDisclosureResponse",
    "EditorialAnalyticsResponse",
    "EditorialAnalyticsSummary",
    "EditorialVelocityWeek",
    "PlagiarismCheckResponse",
    "SeoAnalysisResponse",
]
