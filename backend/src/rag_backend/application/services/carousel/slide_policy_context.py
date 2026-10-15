"""Per-slide contract context for the content drafter (AE-0375, ADR-0021)."""

from __future__ import annotations

from rag_backend.application.services.carousel.content_mode_brief import (
    ContentModeBrief,
)
from rag_backend.application.services.carousel.outline_normalize import (
    OUTLINE_FIELD_ROLE,
    OUTLINE_FIELD_SLIDE_INDEX,
    OUTLINE_FIELD_TITLE,
)
from rag_backend.application.services.carousel.presentation_policy import (
    render_presentation_policy_context,
)
from rag_backend.domain.constants.presentation_roles import ROLE_HOOK
from rag_backend.domain.models.pov_prompts import (
    PovSlideContext,
    PovThesis,
    SlidePolicyContext,
)


def _role(mode: ContentModeBrief, slide: dict[str, object]) -> str:
    role = slide.get(OUTLINE_FIELD_ROLE)
    if isinstance(role, str) and role:
        return role
    index = slide.get(OUTLINE_FIELD_SLIDE_INDEX)
    return (mode.role_at(index) if isinstance(index, int) else None) or ""


def _hook_text(mode: ContentModeBrief, slide: dict[str, object], role: str) -> str:
    """The owner's pick, else the outline's slide-1 title (candidate #1)."""
    if role != ROLE_HOOK:
        return ""
    return mode.hook_text or str(slide.get(OUTLINE_FIELD_TITLE, ""))


def _pov_context(mode: ContentModeBrief, slide: dict[str, object]) -> PovSlideContext:
    role = _role(mode, slide)
    return PovSlideContext(
        pov=PovThesis(
            thesis=mode.thesis,
            personal_proof=mode.personal_proof,
            pov_format=mode.pov_format,
        ),
        role=role,
        slide_count=mode.policy.slide_count,
        hook_text=_hook_text(mode, slide, role),
        cta_copy=mode.cta_sentence(),
    )


def slide_policy_context(
    mode: ContentModeBrief | None, slide: dict[str, object]
) -> SlidePolicyContext | None:
    """None for fixed contracts (legacy drafting); else the sized contract."""
    if mode is None or not mode.has_roles:
        return None
    role = _role(mode, slide)
    return SlidePolicyContext(
        policy_version=mode.policy.version,
        slide_count=mode.policy.slide_count,
        pov=_pov_context(mode, slide) if mode.is_pov else None,
        policy_context=render_presentation_policy_context(mode.policy),
        role=role,
        hook_text=_hook_text(mode, slide, role),
    )


__all__ = ["slide_policy_context"]
