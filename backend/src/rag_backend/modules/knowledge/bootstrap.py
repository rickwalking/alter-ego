"""Composition root for the knowledge module — manual constructor injection.

``bootstrap_module`` wires the knowledge application service to its
collaborators explicitly. There is no DI framework and no global container
lookup inside the module (ADR-0009 §9) — the inbound edge constructs the
request-scoped collaborators (which enlist in the request's Unit of Work) and
passes them in.

**Behavior-preserving wiring (AE-0089).** The knowledge adapters are NOT
relocated in Phase 2; they remain at their legacy locations. The inbound caller
builds them exactly as the legacy routes do today (the request-scoped
``DocumentRepository``, the ``DocumentProcessingPipeline`` injected with that
repository, and the hybrid ``Retriever``) and hands them to this bootstrap. The
collaborators are accepted via the typed :class:`KnowledgeAdapters` bundle so
the function keeps to a single grouped argument (backend/CLAUDE.md ≤3 args).

The ``PlatformServices`` protocol is a local placeholder (as in the reference
template) so the module is importable and type-clean before
``rag_backend.platform`` ships. A real module reads database/session factories
and telemetry from it to build adapters here once it exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from rag_backend.modules.knowledge.application.service import (
    DocumentPipelinePort,
    KnowledgeService,
    RetrieverPort,
)
from rag_backend.modules.knowledge.domain.ports import DocumentRepository


class PlatformServices(Protocol):
    """Placeholder for the shared platform substrate passed to bootstrap.

    Replaced by ``rag_backend.platform.PlatformServices`` once it exists.
    """


@dataclass(frozen=True)
class KnowledgeAdapters:
    """Pre-constructed, request-scoped collaborators for the knowledge module.

    Built at the inbound edge (the api adapter / legacy route) from the existing
    infrastructure so the module wires to them without relocation (AE-0089).
    """

    repository: DocumentRepository
    pipeline: DocumentPipelinePort
    retriever: RetrieverPort


def bootstrap_module(
    platform: PlatformServices,
    adapters: KnowledgeAdapters,
) -> KnowledgeService:
    """Wire the knowledge module and return its public application service.

    ``platform`` is accepted to demonstrate the ADR-0009 §9 bootstrap signature
    (a real module builds adapters from it once ``rag_backend.platform`` ships).
    For the behavior-preserving phase the caller supplies the already-built
    legacy adapters via ``adapters``; this function injects them into the
    application service via the constructor.
    """
    _ = platform  # real modules construct adapters from platform services
    return KnowledgeService(
        repository=adapters.repository,
        pipeline=adapters.pipeline,
        retriever=adapters.retriever,
    )
