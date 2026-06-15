"""Search documents tool for the RAG agent.

The bound tool resolves hybrid search through the knowledge module's public
facade (:class:`KnowledgeSearchPort`) rather than reaching past the module to a
raw retriever, so agent retrieval goes through the same search path as
``/api/search`` (AE-0093). Result formatting is unchanged.
"""

from langchain_core.tools import BaseTool, tool

from rag_backend.infrastructure.logging import get_logger
from rag_backend.modules.knowledge import KnowledgeSearchPort, SearchQuery

logger = get_logger()


@tool
async def search_documents(query: str) -> str:
    """Search the knowledge base for relevant information.

    Use this tool when you need to find specific information
    from the uploaded documents.

    Args:
        query: The search query string
    """
    raise NotImplementedError(
        "Use build_search_documents_tool() to create a bound instance"
    )


def build_search_documents_tool(
    search: KnowledgeSearchPort,
    *,
    top_k: int = 5,
    namespace_prefix: str | None = None,
) -> "BaseTool":
    """Return a bound search_documents tool closure.

    Captures the knowledge search facade so the tool can be used without passing
    it at call time. Search resolves through the module's public facade
    (:class:`KnowledgeSearchPort`).

    Args:
        search: Knowledge search facade (the public search port)
        top_k: Number of results to return
        namespace_prefix: Optional namespace filter for scoped search
    """

    @tool
    async def _search_documents(query: str) -> str:
        """Search the knowledge base for relevant information.

        Use this tool when you need to find specific information
        from the uploaded documents.

        Args:
            query: The search query string
        """
        search_query = SearchQuery(
            query=query,
            top_k=top_k,
            namespace_prefix=namespace_prefix,
        )
        logger.info(
            "search_documents_called",
            query=query,
            top_k=top_k,
            namespace_prefix=namespace_prefix,
        )
        results = await search.search(search_query)
        if not results:
            logger.info("search_documents_no_results", query=query)
            return "No relevant documents found."

        logger.info("search_documents_found", query=query, count=len(results))

        formatted_results = []
        for i, result in enumerate(results, 1):
            snippet = result.content[:2000].strip()
            formatted_results.append(f"[{i}] {snippet}... (Score: {result.score:.3f})")

        return "\n\n".join(formatted_results)

    return _search_documents
