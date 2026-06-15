"""Outbound ports (Protocols) for the knowledge bounded context.

The five knowledge ports are:

* ``DocumentRepository`` — document persistence;
* ``VectorStore`` — vector upsert/delete/hybrid-search;
* ``EmbeddingService`` — embedding generation;
* ``Retriever`` — hybrid retrieval;
* ``DocumentProcessor`` — chunking/processing.

**Re-export, not relocation (AE-0089 constraint).** These Protocols are
defined in the SHARED protocol files under ``rag_backend.domain.protocols.*``
which are imported by ~50+ non-knowledge callers (agents, carousel,
conversation, the container). Physically moving the definitions would break
those imports, so this phase keeps the definitions where they are and merely
**re-exports** them here. The legacy import paths
(``rag_backend.domain.protocols.repositories.DocumentRepository`` etc.) keep
resolving to the identical Protocol objects, while the module domain layer also
exposes them as its own ports. Per backend/CLAUDE.md, interfaces are
``typing.Protocol``, never ABCs.
"""

from __future__ import annotations

from rag_backend.domain.protocols.ai import DocumentProcessor
from rag_backend.domain.protocols.repositories import DocumentRepository
from rag_backend.domain.protocols.vector import (
    EmbeddingService,
    Retriever,
    VectorStore,
)

__all__ = [
    "DocumentProcessor",
    "DocumentRepository",
    "EmbeddingService",
    "Retriever",
    "VectorStore",
]
