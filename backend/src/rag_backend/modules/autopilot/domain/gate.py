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
    """What the runner should do with the current gate.

    ``REDRIVE`` re-runs a parked pending node without sending a review decision.
    """

    APPROVE = "approve"
    REVISE = "revise"
    ESCALATE = "escalate"
    STOP = "stop"
    WAIT = "wait"
    REDRIVE = "redrive"


class StartStatus(StrEnum):
    """Outcome of an in-process workflow start."""

    STARTED = "started"
    PROVIDER_OUTAGE = "provider_outage"


class ResumeStatus(StrEnum):
    """Outcome of one approve or revise.

    ``IN_PROGRESS``: a run is already in flight. ``NOT_PARKED``: a re-drive found no
    parked node. Neither changes anything.
    """

    APPLIED = "applied"
    VERSION_CONFLICT = "version_conflict"
    REVISION_CAP = "revision_cap"
    PROVIDER_OUTAGE = "provider_outage"
    IN_PROGRESS = "in_progress"
    NOT_PARKED = "not_parked"


@dataclass(frozen=True, kw_only=True)
class PolicyDecision:
    """The policy result for one snapshot.

    ``detail`` is what an escalation tells the owner beyond the reason (the slides
    the model fix gave up on). It is empty for every policy decision.
    """

    action: GateAction
    reason: str
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
    """One blocking presentation rule on one slide.

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
    """Inputs for one snapshot. One object keeps the assembler at one argument.

    ``engine_blocker`` is the engine's own content-approve verdict (an error code),
    empty when it would accept, so the policy can revise instead of approving into a
    refusal. ``parked`` means no run is in flight and the checkpoint neither waits
    for a review nor failed; it is ``parked_overdue`` once the grace period passed.
    ``hero_images_total`` counts the hero images the image phase builds (the CTA
    slide has none). A ``pov`` carousel must be voice-scored at the content gate.
    ``quote_violations`` are ``pov_news`` quote cards that are not verbatim.
    """

    state: Mapping[str, object]
    images: tuple[ImageFact, ...]
    slides_total: int
    lock_version: int
    stale: bool
    engine_blocker: str = ""
    parked: bool = False
    parked_overdue: bool = False
    hero_images_total: int = 0
    pov: bool = False
    quote_violations: tuple[QualityViolation, ...] = ()


@dataclass(frozen=True, kw_only=True)
class GateSnapshot:
    """Deterministic facts for one gate. No workflow engine types.

    The images gate expects ``hero_images_total`` hero images, not ``slides_total``.
    ``quality_violations`` are the blocking presentation rules of the content and
    design gates, kept apart from ``forbidden_hits`` so each is reported under its
    own reason. ``pending_rescores`` lists slides whose stored voice score is stale
    (``rescore_pending``): the gate must not approve on a stale passing score, so
    the step re-scores these before approving.
    """

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
    hero_images_total: int = 0
    quality_violations: tuple[QualityViolation, ...] = ()
    pending_rescores: tuple[int, ...] = ()
    pov: bool = False


@dataclass(frozen=True, kw_only=True)
class ProjectSpec:
    """Fields the runner copies from the topic candidate onto a carousel.

    The driver always sets the OpenAI image model and the auto palette;
    ``image_style`` and ``image_guidance`` come from the topic. ``content_mode`` is
    Radar IA or POV, and a POV run carries the owner-confirmed ``pov_thesis``.
    ``pov_format`` and ``slide_count`` are the scout's (defaults applied),
    ``persona_id`` voices and scores the carousel, and ``hook_asset_id`` is the
    slide-1 photo. ``quotes`` are the scout-verified quotes of a ``pov_news`` topic;
    ``cover`` is the GrokBot cover the owner chose for slide 1 (None keeps the
    default).
    """

    topic: str
    audience: str
    niche: str
    brief: str
    sources: tuple[str, ...]
    owner_user_id: str
    image_style: str = DEFAULT_IMAGE_STYLE
    image_guidance: str = ""
    content_mode: str = CONTENT_MODE_NEWS_ANALYSIS
    pov_thesis: str | None = None
    pov_format: str | None = None
    slide_count: int | None = None
    persona_id: str | None = None
    hook_asset_id: str | None = None
    quotes: tuple[NewsQuote, ...] = ()
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
    """Re-run the parked pending node at the current lock version."""

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
