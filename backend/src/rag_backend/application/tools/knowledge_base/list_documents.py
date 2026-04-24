"""List documents tool for the RAG agent."""

from langchain_core.tools import tool

from rag_backend.domain.models import DocumentStatus
from rag_backend.domain.protocols import DocumentRepository


@tool
async def list_documents() -> str:
    """List all available documents in the knowledge base.

    Use this to see what information is available.
    """
    raise NotImplementedError("Use build_list_documents_tool() to create a bound instance")


def build_list_documents_tool(document_repository: DocumentRepository) -> ...:
    """Return a bound list_documents tool closure.

    Captures the repository dependency so the tool can be used
    without passing it at call time.
    """

    @tool
    async def _list_documents() -> str:
        """List all available documents in the knowledge base.

        Use this to see what information is available.
        """
        docs = await document_repository.get_all(status=DocumentStatus.COMPLETED, limit=20)
        if not docs:
            return "No documents found in the knowledge base."

        formatted_docs = []
        for doc in docs:
            formatted_docs.append(f"- {doc.title} ({doc.chunk_count} chunks)")

        return "Available documents:\n" + "\n".join(formatted_docs)

    return _list_documents
