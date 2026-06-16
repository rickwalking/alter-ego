"""Read-model projection results for the publishing bounded context (AE-0131).

The publishing context serves the public/editor READ surfaces — the public
carousel ``/blog`` (+lang), the content-calendar, the workflow-board, and the
editorial-analytics dashboard — from typed **projection results** instead of
exposing the carousel/blog aggregates (or the ORM) across the boundary. These
value objects are the boundary-safe shapes the publishing facade returns; the
thin HTTP route adapters map them one-to-one onto the existing response schemas,
byte-identical to the pre-AE-0131 reads.

They are fully-typed (no ``Any``), immutable, and free of any ORM type — the only
code that touches the carousel/blog ORM for these reads is the read-side ACL in
``infrastructure`` (the sole read owner) behind the
:class:`~rag_backend.modules.publishing.domain.ports.PublishingReadPort`.

Behavior-preserving + additive (AE-0131): the carousel-blog projection reads the
``blog_posts`` ``origin='carousel'`` projection rows backfilled by AE-0127 when
present, FALLING BACK per-field to the embedded carousel columns where the
backfill does not cover a field — so the response is unchanged. No embedded
column is dropped (deferred follow-up, AE-0133).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class CalendarQuery:
    """Inputs for the content-calendar projection (keeps the port ≤3 args).

    ``author_id`` is ``None`` for an admin caller (all authors) and the caller's
    id otherwise — exactly the legacy ``ContentCalendarService`` author filter.
    """

    start: datetime
    end: datetime
    author_id: str | None = None


@dataclass(frozen=True)
class BoardQuery:
    """Inputs for the workflow-board projection.

    ``author_id`` is ``None`` for an admin caller (all projects) and the caller's
    id otherwise; the board scopes a non-admin to projects they own OR review —
    exactly the legacy route filter.
    """

    author_id: str | None = None


@dataclass(frozen=True)
class BlogListQuery:
    """Inputs for the blog-post list projection (mirrors the legacy list query).

    ``author_id`` is the resolved filter (the admin's chosen author or the
    caller's id); the remaining fields mirror the legacy
    ``_BlogPostListQuery`` filters one-for-one.
    """

    status_filter: str | None = None
    author_id: str | None = None
    search: str | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class AnalyticsQuery:
    """Inputs for the editorial-analytics projection.

    ``author_id`` is ``None`` for an admin caller; ``weeks`` is the velocity
    window — exactly the legacy route/service parameters.
    """

    weeks: int = 8
    author_id: str | None = None


@dataclass(frozen=True)
class CarouselBlogProjection:
    """The public carousel ``/blog`` (default pt-BR) read projection.

    Mirrors the fields the ``CarouselBlogResponse`` serializes: the rendered blog
    ``markdown``, the display ``title``, and the optional ``subtitle``.
    """

    markdown: str
    title: str
    subtitle: str | None = None


@dataclass(frozen=True)
class CarouselBlogI18nProjection:
    """The localized carousel ``/blog/{lang}`` read projection.

    Mirrors ``CarouselBlogI18nResponse``: the localized ``markdown`` + resolved
    ``title``/``subtitle`` for the requested ``language`` plus the project's
    ``available_languages`` list.
    """

    markdown: str
    title: str
    subtitle: str | None
    language: str
    available_languages: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CalendarItem:
    """A single content-calendar entry (blog post or carousel).

    Mirrors ``CalendarItemResponse`` exactly so the route maps it field-for-field;
    ``phase``/``phase_status`` are carousel-only, ``is_scheduled`` is blog-only.
    """

    id: str
    content_type: str
    title: str
    status: str
    event_date: str
    is_scheduled: bool = False
    phase: str | None = None
    phase_status: str | None = None


@dataclass(frozen=True)
class CalendarProjection:
    """The content-calendar read projection: the ordered items in the range."""

    items: list[CalendarItem] = field(default_factory=list)


@dataclass(frozen=True)
class BoardCard:
    """A single workflow-board (Kanban) project card.

    Mirrors ``KanbanCardResponse`` so the route maps it field-for-field.
    """

    id: str
    title: str
    topic: str
    current_phase: str
    phase_status: str
    workflow_status: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class BoardColumn:
    """A workflow-board column grouped by phase (mirrors ``KanbanColumnResponse``)."""

    phase: str
    cards: list[BoardCard] = field(default_factory=list)


@dataclass(frozen=True)
class BoardProjection:
    """The workflow-board read projection: the ordered phase columns."""

    columns: list[BoardColumn] = field(default_factory=list)


@dataclass(frozen=True)
class AnalyticsSummary:
    """The editorial-analytics summary (mirrors ``EditorialAnalyticsSummary``)."""

    total_posts: int
    published_this_week: int
    published_this_month: int
    content_velocity_per_week: int
    status_breakdown: dict[str, int]
    average_views: int
    pending_review: int
    draft_count: int
    quality_score_average: float


@dataclass(frozen=True)
class AnalyticsVelocityWeek:
    """A weekly publish-count bucket (mirrors ``EditorialVelocityWeek``)."""

    week_start: str
    published_count: int


@dataclass(frozen=True)
class AnalyticsProjection:
    """The editorial-analytics read projection: the summary + weekly velocity."""

    summary: AnalyticsSummary
    velocity_by_week: list[AnalyticsVelocityWeek] = field(default_factory=list)


__all__ = [
    "AnalyticsProjection",
    "AnalyticsQuery",
    "AnalyticsSummary",
    "AnalyticsVelocityWeek",
    "BlogListQuery",
    "BoardCard",
    "BoardColumn",
    "BoardProjection",
    "BoardQuery",
    "CalendarItem",
    "CalendarProjection",
    "CalendarQuery",
    "CarouselBlogI18nProjection",
    "CarouselBlogProjection",
]
