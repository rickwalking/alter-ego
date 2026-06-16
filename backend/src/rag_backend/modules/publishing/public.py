"""Public facade for the publishing bounded context.

**This file is the module's public API.** Cross-module code SHALL import only
the symbols re-exported here (also re-exported from the package ``__init__``);
everything else under ``rag_backend.modules.publishing.*`` is private to the
module.

The facade exposes:

* ``PublishingService`` / ``PublishingPorts`` — the use-case entry point + its
  optional-ports bundle (scaffolding; AE-0126);
* ``BlogPost`` — the publishing blog-post aggregate VIEW over the ``blog_posts``
  row (new, fully typed); the ``origin`` field is deferred to AE-0127;
* ``Publication`` — the carousel→blog read projection VIEW (new, fully typed);
* ``DistributionChannel`` / ``DistributionChannelKind`` — the distribution-target
  contract (new value objects; adapters land in AE-0129);
* ``PublishingSchedule`` — the release-schedule value object (new, fully typed);
* ``ReleaseState`` / ``ReleasePhase`` — the release-lifecycle projection derived
  from the canonical blog status (new; no new status strings);
* ``BlogPostStatus`` / ``CarouselProject`` / ``BlogPostModel`` — re-exported,
  identical objects, so existing callers keep resolving;
* ``BlogPostRepository`` / ``CarouselRepository`` — the blog + carousel
  persistence ports (re-exported, object-identity shims);
* ``CarouselReleasePort`` / ``BlogVisibilityPort`` / ``BlogSchedulePort`` — the
  release/visibility/schedule write ports (AE-0128);
* ``CarouselReleaseCommand`` — the carousel public-release command DTO (AE-0128);
* ``LegacyPublishingAcl`` — the sole carousel/blog ORM seam (AE-0128), wired at
  the inbound edge into the module's ``PublishingAdapters``;
* ``PublishingAdapters`` / ``PublishingModule`` / ``bootstrap_module`` — the
  composition root (manual constructor injection).

Consumers SHALL NOT import internals such as
``rag_backend.modules.publishing.application.service`` or
``rag_backend.modules.publishing.domain.models`` directly.
"""

from rag_backend.modules.publishing.application.release_command import (
    CarouselReleaseCommand,
    CarouselReleaseHandler,
)
from rag_backend.modules.publishing.application.service import (
    PublishingPorts,
    PublishingService,
)
from rag_backend.modules.publishing.bootstrap import (
    PublishingAdapters,
    PublishingModule,
    bootstrap_module,
)
from rag_backend.modules.publishing.constants import BOARD_PHASES
from rag_backend.modules.publishing.domain.models import (
    BlogPost,
    BlogPostModel,
    BlogPostStatus,
    CarouselProject,
    DistributionChannel,
    DistributionChannelKind,
    DistributionResult,
    Publication,
    PublishingSchedule,
    ReleasePhase,
    ReleaseState,
)
from rag_backend.modules.publishing.domain.ports import (
    BlogPostCrudPort,
    BlogPostRepository,
    BlogSchedulePort,
    BlogVisibilityPort,
    CarouselReleasePort,
    CarouselRepository,
    DistributionPublisher,
    PublishingReadPort,
)
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
from rag_backend.modules.publishing.infrastructure.distribution_channel_adapter import (
    ChannelDistributionPublisher,
)
from rag_backend.modules.publishing.infrastructure.legacy_publishing_acl import (
    LegacyPublishingAcl,
)
from rag_backend.modules.publishing.infrastructure.publishing_port_adapters import (
    AclBlogPostCrudAdapter,
    AclBlogScheduleAdapter,
    AclBlogVisibilityAdapter,
    AclCarouselReleaseAdapter,
    AclPublishingReadAdapter,
)
from rag_backend.modules.publishing.infrastructure.publishing_read_acl import (
    PublishingReadAcl,
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
