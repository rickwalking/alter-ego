"""Infrastructure layer for the presentation bounded context.

Private to the module. Concrete adapters are exposed upward ONLY through the
module's public facade. As of AE-0118 this layer holds the presentation
persistence seam:

* :class:`PresentationWriteOwner` — the single writer of the presentation
  ``carousel_projects`` columns + slide rows and the sole owner of the
  artifact-activation / resume-lock compare-and-swap delegations (the only
  presentation code, alongside the ACL, that imports the carousel / slide ORM);
* :class:`PresentationPersistenceAcl` — the read/write seam translating the
  legacy carousel row to/from the presentation VIEW and routing every write
  through the owner.

The generic carousel persistence adapter is NOT relocated; it remains at its
legacy location and is supplied to the module's ``bootstrap_module`` by the
inbound edge as the re-exported ``CarouselRepository`` port.

As of AE-0119 this layer also holds the image-provider adapters
(:class:`OpenAIImageService` / :class:`GeminiImageService`, implementing the
``ImageGenerationService`` port, and :class:`ImageProviderRegistry`, implementing
the ``ImageProviderPort`` registry contract). These are re-exported from their
legacy locations (object-identity shims); the vendor SDK imports stay inside the
wrapped ``infrastructure.external.*`` classes, never in the presentation
application/domain layers.
"""

from rag_backend.modules.presentation.infrastructure.image_provider_adapters import (
    GeminiImageService,
    ImageProvider,
    ImageProviderRegistry,
    OpenAIImageService,
)
from rag_backend.modules.presentation.infrastructure.presentation_acl import (
    PresentationPersistenceAcl,
    PresentationProjectView,
)
from rag_backend.modules.presentation.infrastructure.presentation_write_owner import (
    PresentationWriteOwner,
)

__all__ = [
    "GeminiImageService",
    "ImageProvider",
    "ImageProviderRegistry",
    "OpenAIImageService",
    "PresentationPersistenceAcl",
    "PresentationProjectView",
    "PresentationWriteOwner",
]
