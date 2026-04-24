"""Carousel pipeline phase subgraphs.

Each phase module exports:
- Node name constants (e.g. ``NODE_RESEARCH``)
- A ``build_*_node(deps)`` factory that returns an async node function

The orchestrator in ``graph.py`` wires phases together with edges.
"""

from rag_backend.application.services.carousel.phases.caption import (
    NODE_CAPTION,
    build_caption_node,
)
from rag_backend.application.services.carousel.phases.constants import (
    NODE_CAPTION as _NODE_CAPTION_C,
)
from rag_backend.application.services.carousel.phases.constants import (
    NODE_CONTENT,
    NODE_DESIGN,
    NODE_EXPORT,
    NODE_FINALIZE,
    NODE_IMAGE_WORKER,
    NODE_IMAGES_COLLECT,
    NODE_IMAGES_DISPATCH,
    NODE_LINKEDIN,
    NODE_PERSIST_SLIDES,
    NODE_RESEARCH,
)
from rag_backend.application.services.carousel.phases.content import (
    NODE_PERSIST_SLIDES as _NODE_PERSIST_SLIDES_C,
)
from rag_backend.application.services.carousel.phases.content import (
    build_content_node,
    build_persist_slides_node,
)
from rag_backend.application.services.carousel.phases.design import (
    NODE_DESIGN as _NODE_DESIGN_C,
)
from rag_backend.application.services.carousel.phases.design import (
    build_design_node,
    build_route_after_design,
)
from rag_backend.application.services.carousel.phases.export import (
    NODE_EXPORT as _NODE_EXPORT_C,
)
from rag_backend.application.services.carousel.phases.export import (
    build_export_node,
)
from rag_backend.application.services.carousel.phases.finalize import (
    NODE_FINALIZE as _NODE_FINALIZE_C,
)
from rag_backend.application.services.carousel.phases.finalize import (
    build_finalize_node,
)
from rag_backend.application.services.carousel.phases.images import (
    NODE_IMAGE_WORKER as _NODE_IMAGE_WORKER_C,
)
from rag_backend.application.services.carousel.phases.images import (
    NODE_IMAGES_COLLECT as _NODE_IMAGES_COLLECT_C,
)
from rag_backend.application.services.carousel.phases.images import (
    NODE_IMAGES_DISPATCH as _NODE_IMAGES_DISPATCH_C,
)
from rag_backend.application.services.carousel.phases.images import (
    build_image_nodes,
)
from rag_backend.application.services.carousel.phases.linkedin import (
    NODE_LINKEDIN as _NODE_LINKEDIN_C,
)
from rag_backend.application.services.carousel.phases.linkedin import (
    build_linkedin_node,
)
from rag_backend.application.services.carousel.phases.research import (
    NODE_RESEARCH as _NODE_RESEARCH_C,
)
from rag_backend.application.services.carousel.phases.research import (
    build_research_node,
)

__all__ = [
    "NODE_CAPTION",
    "NODE_CONTENT",
    "NODE_DESIGN",
    "NODE_EXPORT",
    "NODE_FINALIZE",
    "NODE_IMAGES_COLLECT",
    "NODE_IMAGES_DISPATCH",
    "NODE_IMAGE_WORKER",
    "NODE_LINKEDIN",
    "NODE_PERSIST_SLIDES",
    "NODE_RESEARCH",
    "build_caption_node",
    "build_content_node",
    "build_design_node",
    "build_export_node",
    "build_finalize_node",
    "build_image_nodes",
    "build_linkedin_node",
    "build_persist_slides_node",
    "build_research_node",
    "build_route_after_design",
]
