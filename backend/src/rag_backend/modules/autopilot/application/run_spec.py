"""Build the carousel spec of a queued run (split from ``runner.py``).

AE-0377: a POV run carries the owner-confirmed thesis and uses the POV
photo preset; ``needs_thesis`` keeps a POV run from starting before that.
PR #106 review: the spec also carries the scout's POV format and slide count
(defaults only when the scout left them out), the autopilot persona (so the
content phase scores voice) and, for POV, the owner's slide-1 photo. A POV
spec without that photo must not create a carousel.
"""

from __future__ import annotations

from dataclasses import replace

from rag_backend.domain.constants.content_mode import (
    CONTENT_MODE_NEWS_ANALYSIS,
    CONTENT_MODE_POV,
)
from rag_backend.modules.autopilot.constants import REASON_TOPIC_MISSING
from rag_backend.modules.autopilot.domain.carousel_defaults import (
    GuidanceRequest,
    image_guidance_for,
)
from rag_backend.modules.autopilot.domain.gate import ProjectInputs, ProjectSpec
from rag_backend.modules.autopilot.domain.models import AutopilotRun, TopicCandidate
from rag_backend.modules.autopilot.domain.pov_choice import (
    PovChoice,
    resolved_pov_format,
    resolved_slide_count,
)
from rag_backend.modules.autopilot.domain.thesis import is_pov
from rag_backend.modules.autopilot.pov_constants import (
    POV_IMAGE_STYLE,
    REASON_HOOK_PHOTO_MISSING,
)


def project_spec(
    run: AutopilotRun, topic: TopicCandidate, owner_user_id: str
) -> ProjectSpec:
    """The carousel the runner creates for ``run`` from its topic."""
    pov = is_pov(topic)
    choice = PovChoice(pov_format=topic.pov_format, slide_count=topic.slide_count)
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
        pov_format=resolved_pov_format(choice) if pov else None,
        slide_count=resolved_slide_count(choice) if pov else None,
    )


async def with_inputs(spec: ProjectSpec, inputs: ProjectInputs) -> ProjectSpec:
    """Add the persona (every run) and the slide-1 photo (POV runs)."""
    hook_asset_id = None
    if spec.content_mode == CONTENT_MODE_POV:
        hook_asset_id = await inputs.hook_photo_id(spec.owner_user_id)
    return replace(
        spec, persona_id=await inputs.persona_id(), hook_asset_id=hook_asset_id
    )


def spec_refusal(spec: ProjectSpec | None) -> str | None:
    """Why no carousel may be created: no topic, or POV without its photo."""
    if spec is None:
        return REASON_TOPIC_MISSING
    if spec.content_mode == CONTENT_MODE_POV and spec.hook_asset_id is None:
        return REASON_HOOK_PHOTO_MISSING
    return None


def _guidance_request(topic: TopicCandidate) -> GuidanceRequest:
    return GuidanceRequest(
        image_style=topic.image_style,
        niche=topic.niche,
        image_guidance=topic.image_guidance,
    )


__all__ = ["project_spec", "spec_refusal", "with_inputs"]
