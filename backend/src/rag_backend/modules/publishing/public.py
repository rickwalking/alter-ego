"""Public facade for the publishing bounded context.

**This file is the module's public API.** Cross-module code SHALL import only
the symbols re-exported here (also re-exported from the package ``__init__``);
everything else under ``rag_backend.modules.publishing.*`` is private to the
module.

The facade exposes:

* ``PublishingService`` / ``PublishingPorts`` — the use-case entry point + its
  optional-ports bundle (scaffolding);
* ``BlogPost`` — the publishing blog-post aggregate VIEW over the ``blog_posts``
  row (new, fully typed); the ``origin`` field is added by a later migration;
* ``Publication`` — the carousel→blog read projection VIEW (new, fully typed);
* ``DistributionChannel`` / ``DistributionChannelKind`` — the distribution-target
  contract (new value objects; adapters land later);
* ``PublishingSchedule`` — the release-schedule value object (new, fully typed);
* ``ReleaseState`` / ``ReleasePhase`` — the release-lifecycle projection derived
  from the canonical blog status (new; no new status strings);
* ``BlogPostStatus`` / ``CarouselProject`` / ``BlogPostModel`` — re-exported,
  identical objects, so existing callers keep resolving;
* ``BlogPostRepository`` / ``CarouselRepository`` — the blog + carousel
  persistence ports (re-exported, object-identity shims);
* ``CarouselReleasePort`` / ``BlogVisibilityPort`` / ``BlogSchedulePort`` — the
  release/visibility/schedule write ports;
* ``CarouselReleaseCommand`` — the carousel public-release command DTO;
* ``LegacyPublishingAcl`` — the sole carousel/blog ORM seam, wired at
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
from rag_backend.modules.publishing.application.slide_image_urls import (
    SlideImageUrlRequest,
    build_public_slide_image_urls,
)
from rag_backend.modules.publishing.application.story_image import (
    build_public_story_image_url,
    story_image_file,
)
from rag_backend.modules.publishing.bootstrap import (
    PublishingAdapters,
    PublishingModule,
    bootstrap_module,
)
from rag_backend.modules.publishing.constants import BOARD_PHASES
from rag_backend.modules.publishing.domain.instagram_target import (
    InstagramPublishTarget,
    StoryImageTarget,
)
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
from rag_backend.modules.publishing.infrastructure.instagram_target import (
    load_instagram_publish_target,
)
from rag_backend.modules.publishing.infrastructure.legacy_publishing_acl import (
    LegacyPublishingAcl,
)
from rag_backend.modules.publishing.infrastructure.public_visibility import (
    public_blog_visibility_clause,
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
from rag_backend.modules.publishing.infrastructure.story_image_target import (
    prepare_story_image,
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
    "InstagramPublishTarget",
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
    "SlideImageUrlRequest",
    "StoryImageTarget",
    "bootstrap_module",
    "build_public_slide_image_urls",
    "build_public_story_image_url",
    "load_instagram_publish_target",
    "prepare_story_image",
    "public_blog_visibility_clause",
    "story_image_file",
]
