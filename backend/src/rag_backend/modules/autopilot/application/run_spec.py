"""Build the carousel spec of a queued run (split from ``runner.py``).

AE-0377: a POV run carries the owner-confirmed thesis and uses the POV
photo preset; ``needs_thesis`` keeps a POV run from starting before that.
"""

from __future__ import annotations

from rag_backend.domain.constants.content_mode import CONTENT_MODE_NEWS_ANALYSIS
from rag_backend.modules.autopilot.domain.carousel_defaults import (
    GuidanceRequest,
    image_guidance_for,
)
from rag_backend.modules.autopilot.domain.gate import ProjectSpec
from rag_backend.modules.autopilot.domain.models import AutopilotRun, TopicCandidate
from rag_backend.modules.autopilot.domain.thesis import is_pov
from rag_backend.modules.autopilot.pov_constants import POV_IMAGE_STYLE


def project_spec(
    run: AutopilotRun, topic: TopicCandidate, owner_user_id: str
) -> ProjectSpec:
    """The carousel the runner creates for ``run`` from its topic."""
    pov = is_pov(topic)
    return ProjectSpec(
        topic=topic.title,
        audience=topic.audience,
        niche=topic.niche,
        brief=topic.brief,
        sources=topic.sources,
        owner_user_id=owner_user_id,
        image_style=POV_IMAGE_STYLE if pov else topic.image_style,
        image_guidance=image_guidance_for(_guidance_request(topic)),
        content_mode=topic.content_mode or CONTENT_MODE_NEWS_ANALYSIS,
        pov_thesis=run.pov_thesis if pov else None,
    )


def _guidance_request(topic: TopicCandidate) -> GuidanceRequest:
    return GuidanceRequest(
        image_style=topic.image_style,
        niche=topic.niche,
        image_guidance=topic.image_guidance,
    )


__all__ = ["project_spec"]
