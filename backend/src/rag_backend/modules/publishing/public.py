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
* ``PublishingAdapters`` / ``PublishingModule`` / ``bootstrap_module`` — the
  composition root (manual constructor injection).

Consumers SHALL NOT import internals such as
``rag_backend.modules.publishing.application.service`` or
``rag_backend.modules.publishing.domain.models`` directly.
"""

from rag_backend.modules.publishing.application.service import (
    PublishingPorts,
    PublishingService,
)
from rag_backend.modules.publishing.bootstrap import (
    PublishingAdapters,
    PublishingModule,
    bootstrap_module,
)
from rag_backend.modules.publishing.domain.models import (
    BlogPost,
    BlogPostModel,
    BlogPostStatus,
    CarouselProject,
    DistributionChannel,
    DistributionChannelKind,
    Publication,
    PublishingSchedule,
    ReleasePhase,
    ReleaseState,
)
from rag_backend.modules.publishing.domain.ports import (
    BlogPostRepository,
    CarouselRepository,
)

__all__ = [
    "BlogPost",
    "BlogPostModel",
    "BlogPostRepository",
    "BlogPostStatus",
    "CarouselProject",
    "CarouselRepository",
    "DistributionChannel",
    "DistributionChannelKind",
    "Publication",
    "PublishingAdapters",
    "PublishingModule",
    "PublishingPorts",
    "PublishingSchedule",
    "PublishingService",
    "ReleasePhase",
    "ReleaseState",
    "bootstrap_module",
]
