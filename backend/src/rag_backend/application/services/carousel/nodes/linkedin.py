"""Phase 8: voice-cloned LinkedIn posts in PT + EN.

The generator is optional — older callers that didn't wire one get no
LinkedIn posts, and the pipeline still completes.
"""

from __future__ import annotations

from rag_backend.application.services.carousel.nodes.progress import set_progress
from rag_backend.application.services.linkedin_post_generator import (
    LinkedInPostGenerator,
)
from rag_backend.domain.models import CarouselProject
from rag_backend.domain.protocols import CarouselRepository


async def run_linkedin(
    project: CarouselProject,
    *,
    repo: CarouselRepository,
    generator: LinkedInPostGenerator | None,
) -> None:
    """Generate bilingual LinkedIn posts; no-op if the generator is unset."""
    if generator is None:
        return
    await set_progress(project, repo=repo, label="Writing LinkedIn post (PT + EN)")
    pt, en = await generator.generate_both(project)
    if pt is not None:
        project.linkedin_post_pt = pt.text
    if en is not None:
        project.linkedin_post_en = en.text
