"""Outbound ports for autopilot persistence.

Infrastructure adapters implement these Protocols. The domain does not
import the adapters (ADR-0009 §9).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from rag_backend.modules.autopilot.domain.models import (
    AutopilotRun,
    IntegrationCredential,
    TelegramUpdate,
    TopicCandidate,
    TransitionCommand,
)
from rag_backend.modules.autopilot.domain.publish import (
    AtomicPublishResult,
    CarouselMedia,
    PublishAttemptCommand,
    PublishNotice,
    RunListQuery,
    SaveContainerCommand,
    SavePostCommand,
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

    async def finish_container(self, container_id: str) -> str:
        """Poll the container and ``media_publish``. Returns the media id."""
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
