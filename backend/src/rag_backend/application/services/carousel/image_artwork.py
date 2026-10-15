"""Which slides get generated artwork (AE-0376, ADR-0021 D8).

Fixed contracts (v1-v3) keep the slide-type rule of the images node. A role
contract decides per slide: ``image_required`` in the project's sized
contract (POV: only the point slides; Radar IA v4: hook + impact slides).
"""

from __future__ import annotations

from rag_backend.application.services.carousel.presentation_policy_types import (
    PresentationPolicyError,
)
from rag_backend.application.services.carousel.project_policy import project_policy
from rag_backend.domain.models import CarouselProject


def artwork_slide_numbers(project: CarouselProject) -> frozenset[int] | None:
    """The slide numbers that get artwork, or None for the legacy rule."""
    try:
        policy = project_policy(project)
    except PresentationPolicyError:
        return None
    if not policy.has_roles:
        return None
    return frozenset(policy.artwork_slides)


__all__ = ["artwork_slide_numbers"]
