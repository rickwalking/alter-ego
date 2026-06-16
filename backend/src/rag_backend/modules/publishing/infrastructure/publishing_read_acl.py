"""Anti-corruption layer: legacy carousel/blog persistence ↔ publishing READS (AE-0131).

This module is the **single** read-side seam between the publishing bounded
context and the legacy carousel + blog persistence. It is the **only** file under
``rag_backend.modules.publishing`` that imports the carousel/blog ORM for the
public/editor READ surfaces (the carousel ``/blog`` (+lang) projection, the
content-calendar, the workflow-board, the editorial-analytics, and the blog-post
CRUD persistence rows); the publishing application and domain layers stay free of
it (the layering is enforced by check-integrity + the AE-0132 import contract).

Everything it returns is byte-identical to the pre-AE-0131 scattered
route/service reads — only the *ownership* of the read is consolidated here. It
backs two publishing domain ports:

* :class:`PublishingReadPort` — the carousel-blog projection (with the AE-0127
  ``origin='carousel'`` backfill read, falling back per-field to the embedded
  carousel columns), the content-calendar, the workflow-board, and the
  editorial-analytics projections — replicating the legacy ``media.py`` blog
  routes, the :class:`ContentCalendarService`, the ``workflow_board`` route, and
  the :class:`EditorialAnalyticsService` field-for-field.
* :class:`BlogPostCrudPort` — the blog-post CRUD persistence rows
  (``new_post``/``get_post``/``list_summaries``) so the thin blog routes import no
  blog ORM/repository; the routes keep the access checks + audit/event/lock
  orchestration + the single commit (unchanged).

Behavior-preserving (AE-0131): no read here changes a field, a filter, an
ordering, a default, or a 404 condition relative to the legacy paths. The
carousel-blog projection reads the backfill row when present and falls back
per-field so the response is unchanged (no embedded column is dropped).
"""

from __future__ import annotations

from datetime import datetime
from typing import cast

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_backend.application.services.content_calendar_service import (
    ContentCalendarService,
    _CalendarQuery,
)
from rag_backend.application.services.editorial_analytics_service import (
    EditorialAnalyticsService,
)
from rag_backend.domain.constants.blog_post import BlogPostOrigin
from rag_backend.domain.constants.carousel_workflow import (
    PHASE_BRIEF,
    PHASE_FINAL_REVIEW,
    PHASE_PUBLISHED,
    PHASE_STATUS_PENDING,
    WORKFLOW_STATUS_APPROVED_FOR_PUBLISH,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.infrastructure.database.blog_post_repository import (
    BlogPostRepository,
    _BlogPostListQuery,
)
from rag_backend.infrastructure.database.models.blog_post import BlogPostModel
from rag_backend.infrastructure.database.models.carousel import CarouselProjectModel
from rag_backend.modules.publishing.constants import BOARD_PHASES
from rag_backend.modules.publishing.domain.projections import (
    AnalyticsProjection,
    AnalyticsQuery,
    AnalyticsSummary,
    AnalyticsVelocityWeek,
    BlogListQuery,
    BoardCard,
    BoardColumn,
    BoardProjection,
    BoardQuery,
    CalendarItem,
    CalendarProjection,
    CalendarQuery,
    CarouselBlogI18nProjection,
    CarouselBlogProjection,
)
from rag_backend.modules.publishing.infrastructure.read_projection_helpers import (
    extract_first_paragraph,
    extract_title_and_subtitle,
    resolve_blog_body,
)

# Workflow-board phase columns — the single-source-of-truth ordering shared with
# the legacy route alias (byte-identical column order ending in PHASE_PUBLISHED).
_KANBAN_PHASES = BOARD_PHASES

_LANG_EN = "en"


class PublishingReadAcl:
    """Translate legacy carousel/blog reads to publishing projection results.

    Binds the request-scoped session (the single carousel/blog ORM read seam).
    Every method returns a boundary-safe projection value object (never the ORM)
    that the thin HTTP route adapters map one-to-one onto the existing response
    schemas, byte-identical to the pre-AE-0131 reads.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- PublishingReadPort: carousel-blog projection (default pt-BR) ----------
    async def project_carousel_blog(
        self,
        project: CarouselProject,
    ) -> CarouselBlogProjection | None:
        """Project the public carousel blog (default pt-BR), or ``None`` if absent.

        Reads the AE-0127 ``origin='carousel'`` backfill row when present and
        falls back per-field to the embedded carousel columns (``blog_markdown`` /
        ``title or topic`` / ``subtitle``), so the response is byte-identical to
        the legacy ``media.py:get_carousel_blog``. Returns ``None`` when no blog
        body exists (the route maps that to the legacy 404).
        """
        row = await self._carousel_blog_row(str(project.id))
        markdown = resolve_blog_body(row, project.blog_markdown)
        if markdown is None:
            return None
        row_title = cast("str | None", row.title) if row is not None else None
        row_excerpt = cast("str | None", row.excerpt) if row is not None else None
        title = row_title or project.title or project.topic
        subtitle = row_excerpt or project.subtitle
        return CarouselBlogProjection(
            markdown=markdown,
            title=title,
            subtitle=subtitle,
        )

    # --- PublishingReadPort: localized carousel-blog projection ----------------
    async def project_carousel_blog_i18n(
        self,
        project: CarouselProject,
        language: str,
    ) -> CarouselBlogI18nProjection | None:
        """Project the localized carousel blog, or ``None`` if absent in ``language``.

        Byte-identical to the legacy ``media.py:get_carousel_blog_i18n``: resolves
        the localized markdown via ``project.get_blog(language)``, derives the
        title/subtitle from the markdown heading with the English/Portuguese
        fallbacks, and reports ``project.get_available_languages()``.
        """
        blog_content = project.get_blog(language)
        if blog_content is None:
            return None
        title, subtitle = self._resolve_i18n_title_subtitle(
            project, language, blog_content
        )
        return CarouselBlogI18nProjection(
            markdown=blog_content,
            title=title,
            subtitle=subtitle,
            language=language,
            available_languages=project.get_available_languages(),
        )

    # --- PublishingReadPort: content-calendar projection ----------------------
    async def project_calendar(self, query: CalendarQuery) -> CalendarProjection:
        """Project the content-calendar entries (legacy ``ContentCalendarService``)."""
        items = await ContentCalendarService.get_calendar(
            self._session,
            _CalendarQuery(
                start=query.start,
                end=query.end,
                author_id=query.author_id,
            ),
        )
        return CalendarProjection(
            items=[_to_calendar_item(item) for item in items],
        )

    # --- PublishingReadPort: workflow-board projection ------------------------
    async def project_board(self, query: BoardQuery) -> BoardProjection:
        """Project the workflow-board phase columns (legacy board route)."""
        projects = await self._board_projects(query.author_id)
        cards_by_phase: dict[str, list[BoardCard]] = {
            phase: [] for phase in _KANBAN_PHASES
        }
        for project in projects:
            phase, card = _to_board_card(project)
            cards_by_phase.setdefault(phase, []).append(card)
        columns = [
            BoardColumn(phase=phase, cards=cards_by_phase.get(phase, []))
            for phase in _KANBAN_PHASES
        ]
        return BoardProjection(columns=columns)

    # --- PublishingReadPort: editorial-analytics projection -------------------
    async def project_analytics(self, query: AnalyticsQuery) -> AnalyticsProjection:
        """Project the editorial-analytics summary + weekly velocity.

        Byte-identical to the legacy ``EditorialAnalyticsService`` aggregation: the
        same summary counts, status breakdown, averages, and weekly velocity
        buckets.
        """
        service = EditorialAnalyticsService()
        summary = await service.get_summary(self._session, author_id=query.author_id)
        velocity = await service.get_velocity_by_week(
            self._session, weeks=query.weeks, author_id=query.author_id
        )
        return AnalyticsProjection(
            summary=_to_analytics_summary(summary),
            velocity_by_week=[_to_velocity_week(week) for week in velocity],
        )

    # --- BlogPostCrudPort: blog-post persistence rows -------------------------
    @staticmethod
    def new_post(payload: dict[str, object]) -> BlogPostModel:
        """Build an unsaved blog row from the create payload (legacy from_entity)."""
        return BlogPostModel.from_entity(payload)

    async def get_post(self, post_id: str) -> BlogPostModel | None:
        """Load a blog row by id through the request session, or ``None``."""
        return await self._session.get(BlogPostModel, post_id)

    async def list_summaries(
        self,
        query: BlogListQuery,
    ) -> tuple[list[BlogPostModel], int]:
        """List blog summaries + total count (legacy ``BlogPostRepository``)."""
        return await BlogPostRepository.list_summaries(
            self._session,
            _BlogPostListQuery(
                status_filter=query.status_filter,
                author_id=query.author_id,
                search=query.search,
                limit=query.limit,
                offset=query.offset,
            ),
        )

    # --- internal read helpers ------------------------------------------------
    async def _carousel_blog_row(self, project_id: str) -> BlogPostModel | None:
        """Return the AE-0127 ``origin='carousel'`` backfill row, or ``None``."""
        query = select(BlogPostModel).where(
            BlogPostModel.project_id == project_id,
            BlogPostModel.origin == BlogPostOrigin.CAROUSEL.value,
        )
        result = await self._session.execute(query)
        return result.scalars().first()

    @staticmethod
    def _resolve_i18n_title_subtitle(
        project: CarouselProject,
        language: str,
        blog_content: str,
    ) -> tuple[str, str | None]:
        """Resolve the localized title/subtitle (legacy en/pt fallback chain)."""
        translated_title, translated_subtitle = extract_title_and_subtitle(blog_content)
        if language == _LANG_EN:
            title = (
                translated_title or project.title_en or project.title or project.topic
            )
            subtitle = (
                translated_subtitle
                or project.subtitle_en
                or extract_first_paragraph(blog_content)
                or project.subtitle
            )
            return title, subtitle
        title = translated_title or project.title or project.topic
        subtitle = translated_subtitle or project.subtitle
        return title, subtitle

    async def _board_projects(
        self,
        author_id: str | None,
    ) -> list[CarouselProjectModel]:
        """Load the board's carousel rows (legacy admin/owner-or-reviewer scope)."""
        query = select(CarouselProjectModel).where(
            CarouselProjectModel.phase_status != PHASE_STATUS_PENDING,
        )
        if author_id is not None:
            query = query.where(
                or_(
                    CarouselProjectModel.owner_id == author_id,
                    CarouselProjectModel.assigned_reviewer_id == author_id,
                )
            )
        result = await self._session.execute(query)
        return list(result.scalars().all())


def _to_calendar_item(item: dict[str, object]) -> CalendarItem:
    """Map a legacy calendar dict entry to the projection value object."""
    return CalendarItem(
        id=str(item["id"]),
        content_type=str(item["content_type"]),
        title=str(item["title"]),
        status=str(item["status"]),
        event_date=str(item["event_date"]),
        is_scheduled=bool(item.get("is_scheduled")),
        phase=_optional_str(item.get("phase")),
        phase_status=_optional_str(item.get("phase_status")),
    )


def _to_board_card(project: CarouselProjectModel) -> tuple[str, BoardCard]:
    """Map a carousel row to its (phase, card) — legacy ``workflow_board`` logic."""
    topic = cast("str", project.topic)
    title = cast("str | None", project.title)
    updated_at = cast("datetime | None", project.updated_at)
    phase = project.current_phase or PHASE_BRIEF
    if phase not in _KANBAN_PHASES:
        phase = PHASE_PUBLISHED if project.is_public else PHASE_FINAL_REVIEW
    display_status = project.phase_status or PHASE_STATUS_PENDING
    workflow_status = getattr(project, "workflow_status", None)
    if workflow_status == WORKFLOW_STATUS_APPROVED_FOR_PUBLISH:
        display_status = WORKFLOW_STATUS_APPROVED_FOR_PUBLISH
    card = BoardCard(
        id=str(project.id),
        title=title or topic,
        topic=topic,
        current_phase=phase,
        phase_status=display_status,
        workflow_status=str(workflow_status) if workflow_status else None,
        updated_at=updated_at.isoformat() if updated_at else None,
    )
    return phase, card


def _to_analytics_summary(summary: dict[str, object]) -> AnalyticsSummary:
    """Map the legacy analytics summary dict to the projection value object."""
    breakdown = summary["status_breakdown"]
    status_breakdown: dict[str, int] = (
        {str(k): int(v) for k, v in breakdown.items()}
        if isinstance(breakdown, dict)
        else {}
    )
    return AnalyticsSummary(
        total_posts=int(_as_number(summary["total_posts"])),
        published_this_week=int(_as_number(summary["published_this_week"])),
        published_this_month=int(_as_number(summary["published_this_month"])),
        content_velocity_per_week=int(_as_number(summary["content_velocity_per_week"])),
        status_breakdown=status_breakdown,
        average_views=int(_as_number(summary["average_views"])),
        pending_review=int(_as_number(summary["pending_review"])),
        draft_count=int(_as_number(summary["draft_count"])),
        quality_score_average=float(_as_number(summary["quality_score_average"])),
    )


def _to_velocity_week(week: dict[str, object]) -> AnalyticsVelocityWeek:
    """Map a legacy weekly-velocity dict bucket to the projection value object."""
    return AnalyticsVelocityWeek(
        week_start=str(week["week_start"]),
        published_count=int(_as_number(week["published_count"])),
    )


def _optional_str(value: object) -> str | None:
    """Return ``str(value)`` or ``None`` (preserves the legacy nullable fields)."""
    if value is None:
        return None
    return str(value)


def _as_number(value: object) -> float:
    """Narrow a summary value to a number for the typed projection (no ``Any``)."""
    if isinstance(value, (int, float)):
        return value
    return 0.0


__all__ = ["PublishingReadAcl"]
