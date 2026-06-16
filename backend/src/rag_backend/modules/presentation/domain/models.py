"""Domain entities and value objects for the presentation bounded context.

The presentation context owns the *visual contract* over a carousel project: the
versioned presentation policy (slide budgets, geometry, fonts), the per-slide
presentation copy / validation shapes, and a read view over the carousel row's
presentation fields. This module defines its own new value objects —
:class:`PresentationProject`, :class:`DesignPolicy`, :class:`SlideView` — fully
typed (no ``Any``), and **re-exports** the existing presentation/slide types so
existing callers keep resolving to the IDENTICAL objects.

**Re-export, not relocation (AE-0117 constraint).** The presentation policy
dataclasses continue to live at
``rag_backend.application.services.carousel.presentation_policy_types``; the
per-slide presentation/validation Pydantic models live at
``rag_backend.domain.models.carousel_presentation``; the carousel slide entity
lives at ``rag_backend.domain.models``. This module re-exports them under the
module's domain namespace WITHOUT moving or modifying the canonical definitions,
so identity/isinstance checks and persistence adapters keep working during the
behavior-preserving phase.

The :class:`PresentationProject` is a VIEW over the carousel row's presentation
fields (policy version/checksum, artifact version, creator watermark, design
tokens, template/layout strategy); it does NOT own the carousel aggregate or its
editorial workflow (that is the editorial context, AE-0108). It wraps the
canonical :class:`CarouselProject` (re-exported, identical object) and reads its
presentation-relevant fields without modifying or relocating it.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from rag_backend.application.services.carousel.presentation_policy_types import (
    CarouselPresentationPolicy,
    FontPolicy,
    GeometryBudget,
    PresentationPolicyError,
    SlideTypePolicy,
    TextBudget,
    VisibleTextPolicy,
    VisibleTextRule,
)
from rag_backend.domain.models import (
    CarouselProject,
    CarouselSlide,
)
from rag_backend.domain.models.carousel import DesignTokens
from rag_backend.domain.models.carousel_presentation import (
    ContentSlideCopy,
    SlideValidationReport,
    SlideValidationViolation,
)


@dataclass(frozen=True)
class DesignPolicy:
    """Value object pairing a project's design tokens with its policy identity.

    Captures the presentation-design contract of a carousel project: the canonical
    :class:`DesignTokens` (re-exported, identical type) plus the versioned policy
    identity stamped on the carousel row (``presentation_policy_version`` /
    ``presentation_policy_checksum``) and the template/layout-strategy selectors.
    All fields are explicitly typed; this value object reads existing carousel
    fields without changing render behavior.
    """

    template_version: str
    design_tokens: DesignTokens | None = None
    policy_version: str | None = None
    policy_checksum: str | None = None
    slide_layout_strategy: str | None = None


@dataclass(frozen=True)
class SlideView:
    """Read view over a single carousel slide's presentation fields.

    A lightweight, immutable projection of the canonical :class:`CarouselSlide`
    (re-exported, identical object) exposing the fields the presentation context
    renders/validates — the slide number/type, the rendered HTML, and the slide
    image path. It does not modify or relocate the underlying slide entity.
    """

    slide_number: int
    slide_type: str
    heading: str
    body: str
    html_content: str | None = None
    image_path: str | None = None

    @classmethod
    def from_slide(cls, slide: CarouselSlide) -> SlideView:
        """Build a presentation read view from a canonical carousel slide."""
        return cls(
            slide_number=slide.slide_number,
            slide_type=slide.slide_type,
            heading=slide.heading,
            body=slide.body,
            html_content=slide.html_content,
            image_path=slide.image_path,
        )


@dataclass(frozen=True)
class PresentationProject:
    """The presentation aggregate VIEW: a carousel project's visual contract.

    Wraps the canonical :class:`CarouselProject` (re-exported, identical object)
    and exposes its presentation-relevant state — the :class:`DesignPolicy`
    (design tokens + policy identity) and the activation ``artifact_version`` —
    as the presentation context's own read view. It does NOT own the carousel
    aggregate, its editorial workflow, blog/distribution, or publishing; it only
    projects the presentation fields without modifying or relocating the
    underlying carousel entity.
    """

    project: CarouselProject

    @property
    def project_id(self) -> UUID:
        """The identifier of the underlying carousel project."""
        return self.project.id

    @property
    def artifact_version(self) -> str | None:
        """The activation ``artifact_version`` of the presentation artifact."""
        return self.project.artifact_version

    @property
    def design_policy(self) -> DesignPolicy:
        """The project's design/presentation policy view (tokens + identity)."""
        return DesignPolicy(
            template_version=self.project.template_version,
            design_tokens=self.project.design_tokens,
            policy_version=self.project.presentation_policy_version,
            policy_checksum=self.project.presentation_policy_checksum,
            slide_layout_strategy=self.project.slide_layout_strategy,
        )


__all__ = [
    "CarouselPresentationPolicy",
    "CarouselProject",
    "CarouselSlide",
    "ContentSlideCopy",
    "DesignPolicy",
    "DesignTokens",
    "FontPolicy",
    "GeometryBudget",
    "PresentationPolicyError",
    "PresentationProject",
    "SlideTypePolicy",
    "SlideValidationReport",
    "SlideValidationViolation",
    "SlideView",
    "TextBudget",
    "VisibleTextPolicy",
    "VisibleTextRule",
]
