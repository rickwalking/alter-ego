"""Ports of the repost worker tick: studio, prompts, publisher, metrics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from rag_backend.modules.autopilot.domain.insights import InsightMetrics
from rag_backend.modules.autopilot.domain.reels import ReelMedia
from rag_backend.modules.autopilot.domain.repost import Repost
from rag_backend.modules.autopilot.domain.repost_copy import ApprovalNotice


class RepostRenderError(Exception):
    """A render step failed; ``code`` is stored on the draft."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, kw_only=True)
class RenderedFiles:
    """What the studio wrote for one draft."""

    preview: Path
    cover: Path | None
    original_cover: Path | None
    fits_telegram: bool


@dataclass(frozen=True, kw_only=True)
class StudioJob:
    """The draft and its Reel with fresh URLs."""

    repost: Repost
    reel: ReelMedia


@dataclass(frozen=True, kw_only=True)
class PromptDelivery:
    """The files to show and the prompt text with its buttons."""

    files: RenderedFiles
    notice: ApprovalNotice


@dataclass(frozen=True, kw_only=True)
class ContainerRequest:
    """The new Reel's parts."""

    video_url: str
    caption: str
    cover_url: str | None
    share_to_feed: bool
    collaborators: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class ContainerState:
    """A container's ``status_code`` and detail."""

    code: str
    detail: str | None


class RepostStudio(Protocol):
    """Downloads, renders and writes the draft's files."""

    async def prepare(self, job: StudioJob) -> RenderedFiles:
        """The files; raises ``RepostRenderError``."""
        ...

    def public_url(self, repost: Repost, file_name: str) -> str:
        """The keyless URL of one of the draft's files."""
        ...

    def existing(self, repost: Repost, file_name: str) -> Path | None:
        """The file when it exists."""
        ...


class RepostPrompts(Protocol):
    """The owner's Telegram chat."""

    async def deliver(self, delivery: PromptDelivery) -> int | None:
        """Send the preview and prompt; the prompt's message id."""
        ...

    async def edit(self, message_id: int, text: str) -> None:
        """Replace the prompt text and drop its buttons."""
        ...

    async def tell(self, text: str) -> None:
        """A plain message."""
        ...


class ReelPublisher(Protocol):
    """The Graph Reels container flow."""

    async def create(self, request: ContainerRequest) -> str:
        """The container id."""
        ...

    async def status(self, container_id: str) -> ContainerState:
        """The container's state."""
        ...

    async def publish(self, container_id: str) -> str:
        """The new media id."""
        ...

    async def permalink(self, media_id: str) -> str | None:
        """The new media's permalink."""
        ...


class OriginalMetrics(Protocol):
    """The original Reel's last insight snapshot."""

    async def metrics(self, media_id: str) -> InsightMetrics:
        """Empty metrics when nothing is stored."""
        ...


__all__ = [
    "ContainerRequest",
    "ContainerState",
    "OriginalMetrics",
    "PromptDelivery",
    "ReelPublisher",
    "RenderedFiles",
    "RepostPrompts",
    "RepostRenderError",
    "RepostStudio",
    "StudioJob",
]
