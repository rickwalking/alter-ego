"""Outbound ports for autopilot persistence.

Infrastructure adapters implement these Protocols. The domain does not
import the adapters (ADR-0009 §9).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from rag_backend.modules.autopilot.domain.gate import (
    AttachProjectCommand,
    StartAttemptCommand,
)
from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    IntegrationCredential,
    TelegramUpdate,
    ThesisConfirmCommand,
    TopicCandidate,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.notify import (
    AutopilotOutboxEvent,
    ReviewFacts,
    ReviewNotice,
    ReviewSendResult,
    SaveNoticeLog,
    StatusNotice,
    StatusSendResult,
)
from rag_backend.modules.autopilot.domain.publish import (
    AtomicPublishResult,
    CarouselMedia,
    PublishAttemptCommand,
    PublishNotice,
    RunListQuery,
    SaveContainerCommand,
    SavePostCommand,
    StoredContainer,
)
from rag_backend.modules.autopilot.domain.signals import (
    CollectWindow,
    Signal,
    SignalsBundle,
)
from rag_backend.modules.autopilot.domain.x_status import XStatusTarget


@dataclass(frozen=True, kw_only=True)
class CarouselPublishSnapshot:
    """Carousel facts the publish job checks before calling Graph."""

    workflow_status: str
    status: str
    is_public: bool
    caption: str
    image_urls: tuple[str, ...]
    base_url_configured: bool


class AutopilotRunRepository(Protocol):
    """Persistence port for autopilot runs, including conditional transition."""

    async def add(self, run: AutopilotRun) -> None:
        """Insert a run. The topic row must already exist."""
        ...

    async def get(self, run_id: UUID) -> AutopilotRun | None:
        """Return the run, or None when the id is unknown."""
        ...

    async def transition(self, command: TransitionCommand) -> bool:
        """Compare-and-set the state. False when the expected state is stale."""
        ...

    async def confirm_thesis(self, command: ThesisConfirmCommand) -> bool:
        """AE-0377: store the thesis and move awaiting_thesis -> queued (CAS)."""
        ...

    async def find_by_carousel(self, project_id: str) -> AutopilotRun | None:
        """Return the run for this carousel, or None."""
        ...

    async def list_by_state(self, query: RunListQuery) -> list[AutopilotRun]:
        """Return up to ``query.limit`` runs in ``query.state``, oldest first."""
        ...

    async def save_container(self, command: SaveContainerCommand) -> bool:
        """Store the container id while the run is still publishing."""
        ...

    async def save_post(self, command: SavePostCommand) -> bool:
        """Store the media id and optional permalink while still publishing."""
        ...

    async def record_attempt(self, command: PublishAttemptCommand) -> bool:
        """Bump the attempt counter without leaving ``publishing``."""
        ...

    async def attach_project(self, command: AttachProjectCommand) -> bool:
        """Store the carousel id while the run is still queued."""
        ...

    async def note_start_attempt(self, command: StartAttemptCommand) -> bool:
        """Count a failed workflow start without leaving ``queued``."""
        ...


class PublishCheckpoint(Protocol):
    """Commits the current unit of work so a crash can resume."""

    async def commit(self) -> None:
        """Durably flush the session."""
        ...


class Clock(Protocol):
    """Time source. Tests inject a fixed clock."""

    def now(self) -> datetime:
        """Current timezone-aware instant."""
        ...


class Notifier(Protocol):
    """Sends owner notices. AE-0355's Telegram adapter implements this."""

    async def send_review(self, notice: ReviewNotice) -> ReviewSendResult:
        """Upload the slide album and the action keyboard."""
        ...

    async def send_status(self, notice: StatusNotice) -> StatusSendResult:
        """Send one status or reminder message."""
        ...


class AutopilotEventSource(Protocol):
    """``content.autopilot.*`` outbox rows after a cursor, oldest first."""

    async def recent(self) -> list[AutopilotOutboxEvent]:
        """Return up to the scan limit after the cursor. The caller dedupes."""
        ...

    async def advance(self, event: AutopilotOutboxEvent) -> None:
        """Move the cursor past ``event`` once it is settled."""
        ...


class ReviewFactsSource(Protocol):
    """Loads the private carousel facts a review message needs."""

    async def load(self, project_id: str) -> ReviewFacts | None:
        """Return facts, or None when the carousel does not exist."""
        ...


class NoticeLogStore(Protocol):
    """Persists the notice ledger on the run row."""

    async def save(self, command: SaveNoticeLog) -> None:
        """Write the ledger. Must not change ``updated_at``."""
        ...


class Sleeper(Protocol):
    """Awaitable delay. Tests record the seconds instead of waiting."""

    async def sleep(self, seconds: float) -> None:
        """Pause for ``seconds``."""
        ...


class PublishNotifier(Protocol):
    """Tells the owner a publish finished or failed. AE-0355 sends Telegram."""

    async def notify(self, notice: PublishNotice) -> None:
        """Record or deliver one notice. Must not call Instagram."""
        ...


class CarouselPublishSource(Protocol):
    """Reads the carousel facts the publish pre-checks need."""

    async def load(self, project_id: str) -> CarouselPublishSnapshot | None:
        """Return the snapshot, or None when the project does not exist."""
        ...


class InstagramGraphGateway(Protocol):
    """Graph steps the job calls. Atomic publishers cannot resume a container."""

    def can_resume(self) -> bool:
        """True when container creation and ``media_publish`` are separate calls."""
        ...

    async def current_token(self) -> str:
        """Current access token, possibly empty."""
        ...

    def user_configured(self) -> bool:
        """True when the Instagram user id is set."""
        ...

    async def quota_remaining(self) -> int:
        """Posts still allowed in the current publishing window."""
        ...

    async def open_carousel(self, media: CarouselMedia) -> str:
        """Create the parent container and return its id."""
        ...

    async def was_published(self, container: StoredContainer) -> bool:
        """True when an expired stored container reports ``PUBLISHED``."""
        ...

    async def finish_container(self, container: StoredContainer) -> str:
        """Poll the container and ``media_publish``. Returns the media id."""
        ...

    async def container_status(self, container: StoredContainer) -> str:
        """One read of the container's Graph ``status_code`` (QA r3 Q2)."""
        ...

    async def permalink(self, media_id: str) -> str:
        """Public URL for a published media id."""
        ...

    async def publish_atomic(self, media: CarouselMedia) -> AtomicPublishResult:
        """One-shot publish used when the adapter cannot pause mid-flight."""
        ...


class TopicCandidateRepository(Protocol):
    """Persistence port for scout topic candidates."""

    async def add_topic(self, candidate: TopicCandidate) -> None:
        """Insert a topic candidate."""
        ...

    async def get_topic(self, candidate_id: UUID) -> TopicCandidate | None:
        """Return the candidate, or None when the id is unknown."""
        ...


class IntegrationCredentialRepository(Protocol):
    """Persistence port for encrypted provider tokens."""

    async def add_credential(self, credential: IntegrationCredential) -> None:
        """Insert a provider credential."""
        ...

    async def get_credential(self, provider: str) -> IntegrationCredential | None:
        """Return the credential, or None when the provider is unknown."""
        ...


class TelegramUpdateRepository(Protocol):
    """Persistence port for webhook ``update_id`` dedupe."""

    async def add_telegram_update(self, update: TelegramUpdate) -> None:
        """Insert an update id."""
        ...

    async def has_telegram_update(self, update_id: int) -> bool:
        """True when this update id was already stored."""
        ...


@dataclass(frozen=True, kw_only=True)
class WebSearchQuery:
    """One ``ddgs`` text search. The collector never calls x.com itself."""

    text: str
    timelimit: str
    max_results: int


@dataclass(frozen=True, kw_only=True)
class WebSearchHit:
    """A search snippet. ``url`` is untrusted until the status regex accepts it."""

    url: str
    title: str
    snippet: str


class WebSearchClient(Protocol):
    """Async wrapper around the synchronous ``ddgs`` client."""

    async def search(self, query: WebSearchQuery) -> list[WebSearchHit]:
        """Return snippet hits for one query."""
        ...


class XPostResolver(Protocol):
    """Optional enrichment of a status URL. The default implementation is a no-op."""

    async def resolve(self, target: XStatusTarget) -> str | None:
        """Return replacement post text, or None to keep the snippet."""
        ...


class Collector(Protocol):
    """One free signal source. Failures are isolated by ``SignalsService``."""

    def source_name(self) -> str:
        """Stable source id recorded in ``errors[]`` when collection fails."""
        ...

    async def collect(self, window: CollectWindow) -> list[Signal]:
        """Return the signals visible at ``window.as_of``."""
        ...


class SignalsReader(Protocol):
    """The read side the signals route calls."""

    async def collect_all(self) -> SignalsBundle:
        """Return the cached bundle, collecting on a miss."""
        ...


@dataclass(frozen=True, kw_only=True)
class RecordServedUrls:
    """Canonical or raw signal URLs to remember as served at one instant."""

    urls: tuple[str, ...]
    served_at: datetime


@dataclass(frozen=True, kw_only=True)
class HashLookup:
    """Signal hashes to resolve to existing candidate ids."""

    hashes: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class DayWindow:
    """Half-open ``[start, end)`` interval, both timezone-aware."""

    start: datetime
    end: datetime


@dataclass(frozen=True, kw_only=True)
class QueuedRunCommand:
    """A new ``queued`` run for a candidate that was just inserted."""

    run_id: UUID
    topic_candidate_id: UUID
    created_at: datetime


class TopicIntakeStore(Protocol):
    """Reads and writes the facts topic intake needs. The caller commits."""

    async def record_served_urls(self, command: RecordServedUrls) -> None:
        """Upsert served URLs and drop rows older than the allowlist window."""
        ...

    async def urls_served_since(self, since: datetime) -> frozenset[str]:
        """Canonical URLs whose last serve time is at or after ``since``."""
        ...

    async def ids_for_hashes(self, query: HashLookup) -> dict[str, UUID]:
        """Map each known signal hash to its candidate id."""
        ...

    async def carousel_topics_since(self, since: datetime) -> tuple[str, ...]:
        """Carousel ``topic`` values created at or after ``since``."""
        ...

    async def runs_created_between(self, window: DayWindow) -> int:
        """How many autopilot runs were created in the half-open window."""
        ...

    async def news_runs_created_between(self, window: DayWindow) -> int:
        """AE-0377: Radar IA runs (topic mode NULL or news) in the window."""
        ...

    async def add_candidate(self, candidate: TopicCandidate) -> bool:
        """Insert one topic candidate. False when its signal hash already exists."""
        ...

    async def remove_candidate(self, candidate_id: UUID) -> None:
        """AE-0418: delete a candidate this batch inserted (its cover was lost)."""
        ...

    async def lock_intake(self) -> None:
        """Serialize concurrent intake batches for the rest of the transaction."""
        ...

    async def add_queued_run(self, command: QueuedRunCommand) -> None:
        """Insert one run in ``queued``. The candidate row must exist."""
        ...

    async def commit(self) -> None:
        """Commit the current unit of work."""
        ...
