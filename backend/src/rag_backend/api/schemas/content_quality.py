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


class ChannelPublishingSummary(BaseModel):
    """Published counts for one channel (blog, carousel; LinkedIn/TikTok later)."""

    channel: str
    published_total: int
    published_this_week: int
    published_this_month: int


class EditorialAnalyticsSummary(BaseModel):
    """Dashboard analytics summary."""

    total_posts: int
    published_this_week: int
    published_this_month: int
    content_velocity_per_week: int
    status_breakdown: dict[str, int]
    channels: list[ChannelPublishingSummary]
    pending_review: int
    draft_count: int
    quality_score_average: float | None = Field(
        description="Average content rubric score (0-100); null without scores."
    )
    quality_score_count: int = Field(
        description="How many content rubric scores the average is built from."
    )


class EditorialVelocityWeek(BaseModel):
    """Weekly publish count bucket, per channel."""

    week_start: str
    published_count: int
    channels: dict[str, int]


class EditorialAnalyticsResponse(BaseModel):
    """Full analytics response."""

    summary: EditorialAnalyticsSummary
    velocity_by_week: list[EditorialVelocityWeek]


__all__ = [
    "AccessibilityCheckResponse",
    "AiDisclosureResponse",
    "ChannelPublishingSummary",
    "EditorialAnalyticsResponse",
    "EditorialAnalyticsSummary",
    "EditorialVelocityWeek",
    "PlagiarismCheckResponse",
    "SeoAnalysisResponse",
]
