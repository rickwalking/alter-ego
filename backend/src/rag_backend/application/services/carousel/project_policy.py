"""The presentation policy a project is built against (AE-0374, ADR-0021).

Resolves the project's stamped contract and sizes it to the project's slide
count: a ranged contract (``pov_hook_v1``, ``hero_lower_third_v4``) is expanded
to ``project.slide_count`` (or the contract default); a fixed contract (v1-v3)
is returned as loaded.
"""

from __future__ import annotations

from rag_backend.application.services.carousel import presentation_policy
from rag_backend.application.services.carousel.presentation_policy_range import (
    expand_policy_for_count,
)
from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
)
from rag_backend.domain.constants.content_mode import CONTENT_MODE_POV
from rag_backend.domain.constants.presentation_policy import (
    CREATE_TIME_NEWS_PRESENTATION_POLICY_VERSION,
    CREATE_TIME_POV_PRESENTATION_POLICY_VERSION,
    DEFAULT_PRESENTATION_POLICY_VERSION,
)
from rag_backend.domain.models import CarouselProject


def create_time_policy_version(content_mode: str | None) -> str:
    """The contract a new carousel is stamped with: POV, else Radar IA v4."""
    if content_mode == CONTENT_MODE_POV:
        return CREATE_TIME_POV_PRESENTATION_POLICY_VERSION
    return CREATE_TIME_NEWS_PRESENTATION_POLICY_VERSION


def project_slide_count(
    project: CarouselProject, policy: CarouselPresentationPolicy
) -> int:
    """The project's deck size: its own count when the contract accepts it."""
    span = policy.slide_range
    requested = project.slide_count
    if requested is not None and span.accepts(requested):
        return requested
    return span.default


def project_policy(project: CarouselProject) -> CarouselPresentationPolicy:
    """The project's contract, sized to the project's slide count."""
    version = project.presentation_policy_version or DEFAULT_PRESENTATION_POLICY_VERSION
    policy = presentation_policy.load_presentation_policy(version)
    return expand_policy_for_count(policy, project_slide_count(project, policy))


__all__ = ["create_time_policy_version", "project_policy", "project_slide_count"]
