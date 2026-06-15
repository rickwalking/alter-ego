"""Infrastructure layer for the editorial bounded context.

Private to the module. Holds the legacy carousel anti-corruption layer
(:class:`~rag_backend.modules.editorial.infrastructure.legacy_carousel_acl.LegacyCarouselAcl`,
AE-0109) — the **single** seam that translates the legacy ``carousel_projects``
persistence to/from editorial concepts and the only editorial code that imports
the carousel ORM. It reads via the ORM model's own translator and delegates every
workflow-owned write to the AE-0107 ``CarouselProjectWriteOwner``.

The generic carousel persistence adapter is NOT relocated in this phase
(behavior-preserving); it remains at its legacy location and is supplied to the
module's ``bootstrap_module`` by the inbound edge as the re-exported
``CarouselRepository`` port. Full adapter relocation is a later phase (AE-0110).
"""

from rag_backend.modules.editorial.infrastructure.carousel_project_write_owner import (
    CarouselProjectWriteOwner,
)
from rag_backend.modules.editorial.infrastructure.legacy_carousel_acl import (
    EditorialProjectView,
    LegacyCarouselAcl,
)

__all__ = [
    "CarouselProjectWriteOwner",
    "EditorialProjectView",
    "LegacyCarouselAcl",
]
