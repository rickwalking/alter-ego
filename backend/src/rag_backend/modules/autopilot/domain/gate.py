"""Gate snapshots and the editorial driver the runner calls.

Pure data. The infrastructure adapter fills a snapshot from workflow
state; policy decides without calling the editorial module.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from rag_backend.domain.constants.content_mode import CONTENT_MODE_NEWS_ANALYSIS
from rag_backend.domain.models.news_quote import NewsQuote
from rag_backend.domain.models.slide_cover import SlideCover
from rag_backend.modules.autopilot.domain.carousel_defaults import DEFAULT_IMAGE_STYLE


class GateAction(StrEnum):
    """What the runner should do with the current gate."""

    APPROVE = "approve"
    REVISE = "revise"
    ESCALATE = "escalate"
    STOP = "stop"
    WAIT = "wait"
    # AE-0363: re-run a parked pending node (no review decision is sent).
    REDRIVE = "redrive"


class StartStatus(StrEnum):
    """Outcome of an in-process workflow start."""

    STARTED = "started"
    PROVIDER_OUTAGE = "provider_outage"


class ResumeStatus(StrEnum):
    """Outcome of one approve or revise."""

    APPLIED = "applied"
    VERSION_CONFLICT = "version_conflict"
    REVISION_CAP = "revision_cap"
    PROVIDER_OUTAGE = "provider_outage"
    # AE-0363: a run is already in flight; nothing was changed.
    IN_PROGRESS = "in_progress"
    # AE-0363: a re-drive found no parked node; nothing was changed.
    NOT_PARKED = "not_parked"


@dataclass(frozen=True, kw_only=True)
class PolicyDecision:
    """The policy result for one snapshot."""

    action: GateAction
    reason: str
    # AE-0401: what an escalation tells the owner beyond the reason (the
    # slides the model fix gave up on). Empty for every policy decision.
    detail: str = ""


@dataclass(frozen=True, kw_only=True)
class ResearchSourceFact:
    """One research finding the research check can see."""

    content: str
    summary: str
    key_points: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class ImageFact:
    """Measured bytes for one image asset."""

    present: bool
    is_jpeg: bool
    width: int
    height: int


@dataclass(frozen=True, kw_only=True)
class QualityViolation:
    """One blocking presentation rule on one slide (AE-0392).

    ``slide_index`` is None for a carousel-wide rule. ``text`` is the
    offending copy when the field is a plain text field, else empty.
    """

    rule: str
    slide_index: int | None = None
    locale: str = ""
    field: str = ""
    message: str = ""
    text: str = ""


@dataclass(frozen=True, kw_only=True)
class SnapshotParts:
    """Inputs for one snapshot. One object keeps the assembler at one argument."""

    state: Mapping[str, object]
    images: tuple[ImageFact, ...]
    slides_total: int
    lock_version: int
    stale: bool
    # The engine's own content-approve verdict (error code), empty when it
    # would accept. Lets the policy revise instead of approving into a refusal.
    engine_blocker: str = ""
    # AE-0363: no run in flight and the checkpoint neither waits for a review
    # nor failed; overdue once the grace period passed.
    parked: bool = False
    parked_overdue: bool = False
    # AE-0365: hero images the image phase builds (the CTA slide has none).
    hero_images_total: int = 0
    # PR #106 review: a POV carousel must be voice-scored at the content gate.
    pov: bool = False
    # AE-0406: ``pov_news`` quote cards that are not verbatim (content gate).
    quote_violations: tuple[QualityViolation, ...] = ()


@dataclass(frozen=True, kw_only=True)
class GateSnapshot:
    """Deterministic facts for one gate. No workflow engine types."""

    phase: str
    phase_status: str
    lock_version: int
    sources: tuple[ResearchSourceFact, ...]
    outline_count: int
    slides_total: int
    persona_score: float | None
    forbidden_hits: tuple[str, ...]
    presentation_blockers: tuple[str, ...]
    images: tuple[ImageFact, ...]
    revisions_used: int
    stale: bool
    engine_blocker: str = ""
    parked: bool = False
    parked_overdue: bool = False
    # AE-0365: the images gate expects this many hero images, not slides_total.
    hero_images_total: int = 0
    # AE-0392: blocking presentation rules (content and design gates), kept
    # apart from ``forbidden_hits`` so each is reported under its own reason.
    quality_violations: tuple[QualityViolation, ...] = ()
    pov: bool = False


@dataclass(frozen=True, kw_only=True)
class ProjectSpec:
    """Fields the runner copies from the topic candidate onto a carousel."""

    topic: str
    audience: str
    niche: str
    brief: str
    sources: tuple[str, ...]
    owner_user_id: str
    # AE-0361: the carousel always uses the OpenAI image model and the auto
    # palette; the driver sets those. These two come from the topic.
    image_style: str = DEFAULT_IMAGE_STYLE
    image_guidance: str = ""
    # AE-0377: Radar IA or POV; POV carries the owner-confirmed thesis.
    content_mode: str = CONTENT_MODE_NEWS_ANALYSIS
    pov_thesis: str | None = None
    # PR #106 review: the scout's POV format and slide count (defaults applied),
    # the persona that voices and scores the carousel, and the slide-1 photo.
    pov_format: str | None = None
    slide_count: int | None = None
    persona_id: str | None = None
    hook_asset_id: str | None = None
    # AE-0406: the scout-verified quotes of a ``pov_news`` topic.
    quotes: tuple[NewsQuote, ...] = ()
    # AE-0418: the GrokBot cover the owner chose for slide 1 (None = default).
    cover: SlideCover | None = None


@dataclass(frozen=True, kw_only=True)
class StartCommand:
    """Start the workflow for a project that already exists."""

    project_id: str
    spec: ProjectSpec
    phase: str


@dataclass(frozen=True, kw_only=True)
class ResumeCommand:
    """One approve or revise at the current lock version."""

    project_id: str
    action: str
    expected_version: int
    feedback: str
    phase: str
    target_phase: str = ""


@dataclass(frozen=True, kw_only=True)
class RedriveCommand:
    """Re-run the parked pending node at the current lock version (AE-0363)."""

    project_id: str
    expected_version: int
    phase: str


@dataclass(frozen=True, kw_only=True)
class ResumeResult:
    """Whether the resume was applied or must be retried later."""

    status: ResumeStatus


@dataclass(frozen=True, kw_only=True)
class AttachProjectCommand:
    """Link a carousel to a queued run. One row, still queued."""

    run_id: UUID
    project_id: str


@dataclass(frozen=True, kw_only=True)
class StartAttemptCommand:
    """Count a failed start without leaving ``queued``."""

    run_id: UUID
    attempts: int
    reason: str


@dataclass(frozen=True, kw_only=True)
class OwnerReadyNotice:
    """The owner may review this carousel. Emitted once per revision."""

    run_id: UUID
    project_id: str
    revision: int = 0
    persona_score: float | None = None
    sources_count: int = 0


class EditorialDriver(Protocol):
    """In-process editorial operations. No HTTP."""

    async def create_project(self, spec: ProjectSpec) -> str:
        """Create the carousel and return its id."""
        ...

    async def start(self, command: StartCommand) -> StartStatus:
        """Run workflow start until the first gate, or report an outage."""
        ...

    async def read_gate(self, project_id: str) -> GateSnapshot:
        """Read the current gate. Does not resume the workflow."""
        ...

    async def resume(self, command: ResumeCommand) -> ResumeResult:
        """Approve or revise once, using ``expected_version``."""
        ...

    async def redrive(self, command: RedriveCommand) -> ResumeResult:
        """Re-run a parked pending node once. Sends no review decision."""
        ...


class ProjectInputs(Protocol):
    """Who voices a new carousel and which photo opens a POV deck."""

    async def persona_id(self) -> str | None:
        """The autopilot persona (setting, else "Pedro" by name), or None."""
        ...

    async def hook_photo_id(self, owner_user_id: str) -> str | None:
        """The owner's slide-1 photo (library role ``hook``), or None."""
        ...


class OwnerReadyNotifier(Protocol):
    """Records ``content.autopilot.ready_for_owner``. The caller commits."""

    async def notify_ready(self, notice: OwnerReadyNotice) -> None:
        """Stage one ready event. Must not call Telegram."""
        ...
