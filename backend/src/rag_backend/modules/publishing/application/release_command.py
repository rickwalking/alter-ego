"""Carousel public-release command for the publishing bounded context (AE-0128).

Private to the module. The public facade re-exports the command + its result;
cross-module code never imports this path directly.

This command owns the carousel **public-release** write — making a carousel
``is_public`` — that ``crud.py:publish_carousel`` performed inline today. It is a
behavior-preserving CONTRACT RELOCATION (the AE-0111 approval≠release split): the
command does EXACTLY what the legacy route did for the ``is_public`` write — the
same ``is_public=True`` / ``current_phase=published`` mutation on the carousel
entity (via the carousel repository) AND on the carousel ORM row, committed once.
No auto-publish behavior is changed; the route still performs the same
preconditions (approved-for-publish gate, completed-status gate, artifact-health
gate) and the same blog-markdown build BEFORE invoking this command.

The command depends only on contracts: the :class:`CarouselRepository` port and
the :class:`CarouselReleasePort` (whose only adapter is the publishing ACL/owner
in the infrastructure layer). It imports no ORM — the carousel ENTITY is passed
through ``object`` and forwarded to the port, so this application layer stays
ORM-free (AE-0128 layering constraint).
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_backend.modules.publishing.domain.ports import CarouselReleasePort


@dataclass(frozen=True)
class CarouselReleaseCommand:
    """Inputs for the carousel public-release write.

    ``project`` is the canonical carousel project entity already loaded (and, when
    its blog markdown was missing, already updated) by the route BEFORE release —
    passed as ``object`` so this application command imports no carousel ORM/entity
    module. ``project_id`` is its identifier (a string, as the legacy route uses).
    """

    project: object
    project_id: str


class CarouselReleaseHandler:
    """Apply the carousel public-release write via the release port.

    Constructed per request at the inbound edge from the bootstrapped publishing
    module. Holds no framework state and resolves no global container; the release
    port (backed by the publishing ACL/owner, the single carousel-ORM seam) is
    injected via the constructor. The handler never touches the ORM or commits
    directly — it forwards to the port, which performs the byte-identical write +
    the single commit through the platform Unit of Work.
    """

    def __init__(self, release_port: CarouselReleasePort) -> None:
        self._release_port = release_port

    async def release(self, command: CarouselReleaseCommand) -> object:
        """Release the carousel publicly; return the updated carousel entity.

        Byte-identical to the legacy ``crud.py:publish_carousel`` release write:
        forwards to the port, which sets ``is_public=True`` /
        ``current_phase=published`` on the entity (via the repository) and on the
        ORM row, then commits once. Returns the updated entity the route
        serializes.
        """
        return await self._release_port.release_public(
            command.project,
            command.project_id,
        )


__all__ = [
    "CarouselReleaseCommand",
    "CarouselReleaseHandler",
]
