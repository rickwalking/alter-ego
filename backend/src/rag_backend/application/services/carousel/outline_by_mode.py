"""Outline generation by content mode (ADR-0021).

- No brief or a fixed contract (v1-v3): the legacy outline, unchanged.
- Radar IA v4: the outline sized to the project's deck, roles stamped by
  position from the contract.
- "Ponto de Vista": the ``carousel_pov/v1`` outline from the owner's thesis,
  roles stamped by position, five hook candidates on slide 1 and the
  "thesis on slides 1-2" outline check.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import structlog

from rag_backend.application.services.carousel.content_mode_brief import (
    ContentModeBrief,
)
from rag_backend.application.services.carousel.editorial_workflow_support import (
    EditorialWorkflowStartInput,
)
from rag_backend.application.services.carousel.outline_normalize import (
    OUTLINE_FIELD_KEY_POINTS,
    OUTLINE_FIELD_TITLE,
    normalize_editorial_outline,
    stamp_outline_roles,
)
from rag_backend.application.services.carousel.pov_checks import thesis_appears_early
from rag_backend.application.services.carousel.presentation_policy import (
    render_presentation_policy_context,
)
from rag_backend.domain.constants.pov_prompts import (
    OUTLINE_CHECK_THESIS_EARLY,
    OUTLINE_FIELD_HOOK_CANDIDATES,
    OUTLINE_FIELD_OUTLINE_CHECKS,
)
from rag_backend.domain.models.pov_prompts import (
    PovHookRequest,
    PovOutlineRequest,
    PovThesis,
    RadarHookRequest,
    SizedOutlineRequest,
    SlidePolicyContext,
)

logger = structlog.get_logger(__name__)

LOG_HOOK_CANDIDATES_FAILED = "pov_hook_candidates_failed"
_EARLY_SLIDES = 2


class OutlineAgent(Protocol):
    """The outline agent's calls used here (structural: no application->agents import)."""

    async def generate_outline_for(
        self, request: SizedOutlineRequest
    ) -> list[dict[str, object]]: ...

    async def generate_pov_outline(
        self, request: PovOutlineRequest
    ) -> list[dict[str, object]]: ...

    async def hook_candidates(self, request: PovHookRequest) -> list[str]: ...

    async def radar_hook_candidates(self, request: RadarHookRequest) -> list[str]: ...


@dataclass(frozen=True)
class ModeOutlineRequest:
    """The workflow brief plus the project's content-mode brief."""

    workflow_input: EditorialWorkflowStartInput
    brief: ContentModeBrief | None = None

    def source_texts(self) -> list[str]:
        """The source documents' text."""
        return [s.get("content", "") for s in self.workflow_input.sources]


def _sizing(brief: ContentModeBrief) -> SlidePolicyContext:
    return SlidePolicyContext(
        policy_version=brief.policy.version,
        slide_count=brief.policy.slide_count,
        policy_context=render_presentation_policy_context(brief.policy),
        roles=tuple(slide.role or "" for slide in brief.policy.slides),
    )


def _thesis(brief: ContentModeBrief) -> PovThesis:
    return PovThesis(
        thesis=brief.thesis,
        personal_proof=brief.personal_proof,
        pov_format=brief.pov_format,
        prompt_domain=brief.prompt_domain,
        quotes=brief.quotes,
    )


def _slide_text(slide: dict[str, object]) -> str:
    points = slide.get(OUTLINE_FIELD_KEY_POINTS)
    joined = " ".join(str(p) for p in points) if isinstance(points, list) else ""
    return f"{slide.get(OUTLINE_FIELD_TITLE, '')} {joined}"


async def _hooks(
    agent: OutlineAgent, request: ModeOutlineRequest, brief: ContentModeBrief
) -> list[str]:
    """Hook candidates; a failure keeps the outline (the owner can type one).

    POV hooks argue the owner's thesis; Radar IA v4 hooks come from
    the brief and the sources only.
    """
    workflow_input = request.workflow_input
    try:
        if not brief.is_pov:
            return await agent.radar_hook_candidates(
                RadarHookRequest(
                    topic=workflow_input.topic,
                    audience=workflow_input.audience,
                    brief=workflow_input.brief,
                    sources=request.source_texts(),
                )
            )
        return await agent.hook_candidates(
            PovHookRequest(
                topic=workflow_input.topic,
                audience=workflow_input.audience,
                pov=_thesis(brief),
            )
        )
    except (ValueError, TypeError):
        logger.warning(LOG_HOOK_CANDIDATES_FAILED)
        return []


def attach_hook_and_checks(
    outline: list[dict[str, object]],
    brief: ContentModeBrief,
    hooks: list[str],
) -> list[dict[str, object]]:
    """Slide 1 carries the candidates, the chosen hook and the outline checks."""
    if not outline:
        return outline
    first = dict(outline[0])
    first[OUTLINE_FIELD_HOOK_CANDIDATES] = hooks
    chosen = brief.hook_text or (hooks[0] if hooks else "")
    if chosen:
        first[OUTLINE_FIELD_TITLE] = chosen
    early = [_slide_text(slide) for slide in [first, *outline[1:_EARLY_SLIDES]]]
    first[OUTLINE_FIELD_OUTLINE_CHECKS] = {
        OUTLINE_CHECK_THESIS_EARLY: thesis_appears_early(early, brief.thesis),
    }
    return [first, *outline[1:]]


async def _pov_outline(
    agent: OutlineAgent, request: ModeOutlineRequest, brief: ContentModeBrief
) -> list[dict[str, object]]:
    raw = await agent.generate_pov_outline(
        PovOutlineRequest(
            topic=request.workflow_input.topic,
            audience=request.workflow_input.audience,
            brief=request.workflow_input.brief,
            sources=request.source_texts(),
            pov=_thesis(brief),
            roles=tuple(slide.role or "" for slide in brief.policy.slides),
            policy_context=render_presentation_policy_context(brief.policy),
            persona=request.workflow_input.persona,
        )
    )
    outline = normalize_editorial_outline(stamp_outline_roles(raw, brief.policy))
    return attach_hook_and_checks(outline, brief, await _hooks(agent, request, brief))


async def generate_outline_for_mode(
    agent: OutlineAgent, request: ModeOutlineRequest
) -> list[dict[str, object]]:
    """The outline for the project's mode (legacy when there is no role contract)."""
    brief = request.brief
    workflow_input = request.workflow_input
    if brief is not None and brief.is_pov:
        return await _pov_outline(agent, request, brief)
    sizing = _sizing(brief) if brief is not None and brief.has_roles else None
    outline = await agent.generate_outline_for(
        SizedOutlineRequest(
            topic=workflow_input.topic,
            audience=workflow_input.audience,
            brief=workflow_input.brief,
            sources=request.source_texts(),
            sizing=sizing,
        )
    )
    if brief is None or sizing is None:
        return outline
    stamped = normalize_editorial_outline(stamp_outline_roles(outline, brief.policy))
    return attach_hook_and_checks(stamped, brief, await _hooks(agent, request, brief))


__all__ = [
    "ModeOutlineRequest",
    "OutlineAgent",
    "attach_hook_and_checks",
    "generate_outline_for_mode",
]
