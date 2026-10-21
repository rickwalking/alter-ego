"""Command / result value objects for the presentation editorial-port surface.

These typed objects are the data carried across the **editorial → presentation**
boundary. They are deliberately small, frozen, and free of the
carousel ORM: the editorial workflow constructs a command, hands it to a
presentation port through the public facade, and receives a result back. The
ports themselves are defined in :mod:`rag_backend.modules.presentation.domain.ports`;
the concrete adapters that delegate to the unchanged application services live in
:mod:`rag_backend.modules.presentation.infrastructure.editorial_workflow_ports`.

Behavior-preserving: every object mirrors the inputs/outputs the existing
design / images / export / artifact-build call sites already pass — no new
behavior, only a typed contract over what crosses the boundary.

The ``ContentFormatProducer`` extension point (see ``ports``) is a
PRESENTATION-SPECIFIC boundary: :class:`ProduceFormat` is its single command and
:class:`ProducedArtifact` its single result. There is intentionally NO generic
multi-format framework — carousel is the only producer today; a second format
adds a second producer, not an abstraction layer.

The image node reports a progress snapshot through the callback port; editorial owns the
``phase_progress`` workflow-state write and the SSE emission. The snapshot mirrors,
field for field, the dict the legacy image node persisted, so the editorial-side write
stays byte-identical.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProgressSnapshot:
    """An image-generation progress snapshot reported back to editorial.

    Carries exactly the fields the legacy ``_publish_progress_state`` wrote into
    the project's ``phase_progress`` column plus the ``project_id`` and the
    ``sse_phase`` the editorial SSE channel needs. NOTE the two distinct phase
    values the legacy code used: ``phase`` is the value stamped INSIDE the
    ``phase_progress`` dict (``"generating_images"``), while ``sse_phase`` is the
    workflow phase passed to the SSE publisher (``"images"``); they intentionally
    differ and are both preserved byte-identically. The presentation side NEVER
    writes workflow state — it hands this snapshot to the callback and the
    editorial implementation performs the (byte-identical) persist + publish.
    """

    project_id: str
    phase: str
    sse_phase: str
    label: str
    current: int
    total: int
    slides: tuple[dict[str, object], ...]

    def as_phase_progress(self) -> dict[str, object]:
        """Return the ``phase_progress`` dict byte-identical to the legacy write."""
        return {
            "phase": self.phase,
            "label": self.label,
            "current": self.current,
            "total": self.total,
            "slides": [dict(slide) for slide in self.slides],
        }


@dataclass(frozen=True)
class ProduceFormat:
    """Command to produce a renderable presentation artifact for a project.

    The single input to :meth:`ContentFormatProducer.produce`. ``project_id`` is
    the carousel project; ``strategy`` is the optional slide-layout strategy the
    re-render applies (mirroring ``re_render_slides(project_id, strategy=...)``).
    """

    project_id: str
    strategy: str | None = None


@dataclass(frozen=True)
class ProducedArtifact:
    """Result of producing a presentation format.

    Mirrors the outputs the legacy re-render exposes: the PT/EN PDF paths stamped
    on the project. Empty strings mean "not produced" (the legacy code leaves the
    pointer unset). No artifact bytes cross the boundary — only the path/URL
    pointers the refactor must preserve.
    """

    format_name: str
    pdf_path: str = ""
    pdf_path_en: str = ""


@dataclass(frozen=True)
class ArtifactActivation:
    """Outcome of the artifact build + activation CAS.

    ``ok`` is whether the build+activation succeeded; ``artifact_version`` is the
    activated version string (the CAS payload paired with ``lock_version``);
    ``errors`` carries the failure reasons (incl. ``ERR_ARTIFACT_BUILD_CONFLICT``)
    when ``ok`` is false. The compound ``artifact_version`` ↔ ``lock_version`` CAS
    is performed UNCHANGED inside the wrapped service; this object only reports its
    outcome.
    """

    ok: bool
    artifact_version: str = ""
    errors: tuple[str, ...] = field(default_factory=tuple)


__all__ = [
    "ArtifactActivation",
    "ProduceFormat",
    "ProducedArtifact",
    "ProgressSnapshot",
]
