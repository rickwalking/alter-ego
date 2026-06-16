"""Publishing bounded context (Supporting) — AE-0126 Phase 6 skeleton.

The publishing context owns the *release + distribution contract* over a content
item: the blog-post aggregate (over the ``blog_posts`` row), the carousel→blog
read projection, the distribution channels a release targets, and the schedule a
release follows. This package follows the module conventions
(``docs/architecture/module-conventions.md``, AE-0081) and ADR-0009 (Domain
Modular Monolith):

* per-module internal layers — ``domain/``, ``application/``,
  ``infrastructure/``, ``api/``;
* the **public-facade rule** — cross-module code imports ONLY from this
  package's public API (``public.py``, re-exported here);
* manual constructor injection via ``bootstrap_module`` (ADR-0009 §9);
* the Unit-of-Work boundary owned at the application layer (reused from
  ``rag_backend.platform.database``).

Phase 6 is **behavior-preserving + additive** (AE-0126): the blog workflow
status enum, the blog ORM row, the carousel project entity, and the blog +
carousel repository ports are *re-exported* from their canonical locations (no
physical move, object-identity shims). The new ``BlogPost`` / ``Publication`` /
``DistributionChannel`` / ``PublishingSchedule`` / ``ReleaseState`` value objects
model the publishing view. The additive ``origin`` migration, persistence,
distribution, the outbox, and the full carousel→blog projection land in
AE-0127..0131. Publishing is invoked BY editorial/presentation via the facade
(acyclic; publishing imports no editorial/presentation internals).

Cross-module consumers SHALL import from the facade only, e.g.::

    from rag_backend.modules.publishing import PublishingService, Publication
"""

from rag_backend.modules.publishing.public import (
    BOARD_PHASES,
    AclBlogPostCrudAdapter,
    AclBlogScheduleAdapter,
    AclBlogVisibilityAdapter,
    AclCarouselReleaseAdapter,
    AclPublishingReadAdapter,
    AnalyticsProjection,
    AnalyticsQuery,
    AnalyticsSummary,
    AnalyticsVelocityWeek,
    BlogListQuery,
    BlogPost,
    BlogPostCrudPort,
    BlogPostModel,
    BlogPostRepository,
    BlogPostStatus,
    BlogSchedulePort,
    BlogVisibilityPort,
    BoardCard,
    BoardColumn,
    BoardProjection,
    BoardQuery,
    CalendarItem,
    CalendarProjection,
    CalendarQuery,
    CarouselBlogI18nProjection,
    CarouselBlogProjection,
    CarouselProject,
    CarouselReleaseCommand,
    CarouselReleaseHandler,
    CarouselReleasePort,
    CarouselRepository,
    ChannelDistributionPublisher,
    DistributionChannel,
    DistributionChannelKind,
    DistributionPublisher,
    DistributionResult,
    LegacyPublishingAcl,
    Publication,
    PublishingAdapters,
    PublishingModule,
    PublishingPorts,
    PublishingReadAcl,
    PublishingReadPort,
    PublishingSchedule,
    PublishingService,
    ReleasePhase,
    ReleaseState,
    bootstrap_module,
)

__all__ = [
    "BOARD_PHASES",
    "AclBlogPostCrudAdapter",
    "AclBlogScheduleAdapter",
    "AclBlogVisibilityAdapter",
    "AclCarouselReleaseAdapter",
    "AclPublishingReadAdapter",
    "AnalyticsProjection",
    "AnalyticsQuery",
    "AnalyticsSummary",
    "AnalyticsVelocityWeek",
    "BlogListQuery",
    "BlogPost",
    "BlogPostCrudPort",
    "BlogPostModel",
    "BlogPostRepository",
    "BlogPostStatus",
    "BlogSchedulePort",
    "BlogVisibilityPort",
    "BoardCard",
    "BoardColumn",
    "BoardProjection",
    "BoardQuery",
    "CalendarItem",
    "CalendarProjection",
    "CalendarQuery",
    "CarouselBlogI18nProjection",
    "CarouselBlogProjection",
    "CarouselProject",
    "CarouselReleaseCommand",
    "CarouselReleaseHandler",
    "CarouselReleasePort",
    "CarouselRepository",
    "ChannelDistributionPublisher",
    "DistributionChannel",
    "DistributionChannelKind",
    "DistributionPublisher",
    "DistributionResult",
    "LegacyPublishingAcl",
    "Publication",
    "PublishingAdapters",
    "PublishingModule",
    "PublishingPorts",
    "PublishingReadAcl",
    "PublishingReadPort",
    "PublishingSchedule",
    "PublishingService",
    "ReleasePhase",
    "ReleaseState",
    "bootstrap_module",
]
