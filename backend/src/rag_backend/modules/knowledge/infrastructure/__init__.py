"""Infrastructure layer for the knowledge bounded context (private).

**No adapters are physically relocated in Phase 2 (AE-0089).** The concrete
adapters that implement the knowledge ports already exist at their legacy
locations and are imported by other contexts and the container:

* ``rag_backend.infrastructure.database.document_repository`` — DocumentRepository
* ``rag_backend.infrastructure.retrieval.hybrid_retriever`` — Retriever
* ``rag_backend.infrastructure.vector_store.pinecone_store`` — VectorStore
* ``rag_backend.infrastructure.embeddings.openai_embeddings`` — EmbeddingService
* ``rag_backend.infrastructure.retrieval.document_processor`` — DocumentProcessor

plus the pipeline ``rag_backend.application.services.document_pipeline``. The
module's :func:`~rag_backend.modules.knowledge.bootstrap.bootstrap_module`
wires the application service to these existing adapters via manual constructor
injection. Physical relocation into this subpackage is deferred to a later
phase; this package is intentionally empty of adapters for now.
"""
