"""List documents tool for the RAG agent."""

from langchain_core.tools import tool

from rag_backend.domain.models import DocumentStatus
from rag_backend.domain.protocols import DocumentRepository

_LIST_LIMIT = 20
_SCOPED_READ_LIMIT = 100
_NO_DOCUMENTS = "No documents found in the knowledge base."


@tool
async def list_documents() -> str:
    """List all available documents in the knowledge base.

    Use this to see what information is available.
    """
    raise NotImplementedError(
        "Use build_list_documents_tool() to create a bound instance"
    )


def build_list_documents_tool(
    document_repository: DocumentRepository,
    scope_filter: frozenset[str] | None = None,
) -> ...:
    """Return a bound list_documents tool closure.

    Captures the repository dependency so the tool can be used
    without passing it at call time.

    Args:
        document_repository: Document repository instance
        scope_filter: Optional scopes the listed documents must belong to

    With a scope filter the tool reads up to 100 recent completed documents
    and lists the first 20 in those scopes, so recent documents of other
    scopes do not crowd the allowed ones out of the list.
    """

    @tool
    async def _list_documents() -> str:
        """List all available documents in the knowledge base.

        Use this to see what information is available.
        """
        docs = await document_repository.get_all(
            status=DocumentStatus.COMPLETED,
            limit=_LIST_LIMIT if scope_filter is None else _SCOPED_READ_LIMIT,
        )
        if scope_filter is not None:
            docs = [d for d in docs if d.scope.value in scope_filter][:_LIST_LIMIT]
        if not docs:
            return _NO_DOCUMENTS

        formatted_docs = [f"- {doc.title} ({doc.chunk_count} chunks)" for doc in docs]

        return "Available documents:\n" + "\n".join(formatted_docs)

    return _list_documents
