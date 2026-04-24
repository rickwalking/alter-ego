"""Search documents tool for the RAG agent."""

from langchain_core.tools import tool

from rag_backend.domain.models import RetrievalQuery
from rag_backend.domain.protocols import Retriever


@tool
async def search_documents(query: str) -> str:
    """Search the knowledge base for relevant information.

    Use this tool when you need to find specific information
    from the uploaded documents.

    Args:
        query: The search query string
    """
    raise NotImplementedError("Use build_search_documents_tool() to create a bound instance")


def build_search_documents_tool(retriever: Retriever, *, top_k: int = 5) -> ...:
    """Return a bound search_documents tool closure.

    Captures the retriever dependency so the tool can be used
    without passing it at call time.
    """

    @tool
    async def _search_documents(query: str) -> str:
        """Search the knowledge base for relevant information.

        Use this tool when you need to find specific information
        from the uploaded documents.

        Args:
            query: The search query string
        """
        results = await retriever.retrieve(RetrievalQuery(query=query, top_k=top_k))
        if not results:
            return "No relevant documents found."

        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_results.append(f"[{i}] {result.content[:300]}... (Score: {result.score:.3f})")

        return "\n\n".join(formatted_results)

    return _search_documents
