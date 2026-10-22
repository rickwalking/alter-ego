"""Search documents tool for the RAG agent.

The bound tool resolves hybrid search through the knowledge module's public
facade (:class:`KnowledgeSearchPort`) rather than reaching past the module to a
raw retriever, so agent retrieval goes through the same search path as
``/api/search``. Result formatting is unchanged.
"""

import hashlib
from dataclasses import dataclass

from langchain_core.tools import BaseTool, tool

from rag_backend.domain.constants.chat_stream import (
    SEARCH_BUDGET_EXHAUSTED,
    SEARCH_NO_RESULTS,
)
from rag_backend.infrastructure.logging import get_logger
from rag_backend.modules.knowledge import KnowledgeSearchPort, SearchQuery

logger = get_logger()

QUERY_HASH_CHARS = 12


def query_log_fields(query: str) -> dict[str, str | int]:
    """What the logs may say about a search query: its length and a short hash.

    The query is written from the visitor's own words, so its text never goes
    to the logs; the hash still lets repeated searches be correlated.
    """
    digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
    return {"query_length": len(query), "query_hash": digest[:QUERY_HASH_CHARS]}


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


@dataclass(frozen=True)
class SearchToolOptions:
    """How a bound search tool searches.

    ``max_calls`` caps the searches over the tool's lifetime (one chat turn);
    past it the tool answers ``SEARCH_BUDGET_EXHAUSTED`` without searching, so
    the agent stops rephrasing and answers. ``None`` means unlimited.
    """

    top_k: int = 5
    namespace_prefix: str | None = None
    max_calls: int | None = None


def build_search_documents_tool(
    search: KnowledgeSearchPort,
    options: SearchToolOptions | None = None,
) -> "BaseTool":
    """Return a bound search_documents tool closure.

    Captures the knowledge search facade so the tool can be used without passing
    it at call time. Search resolves through the module's public facade
    (:class:`KnowledgeSearchPort`).

    Args:
        search: Knowledge search facade (the public search port)
        options: Result count, namespace filter and search budget
    """
    opts = options or SearchToolOptions()
    top_k = opts.top_k
    namespace_prefix = opts.namespace_prefix
    max_calls = opts.max_calls
    calls_made = 0

    @tool
    async def _search_documents(query: str) -> str:
        """Search the knowledge base for relevant information.

        Use this tool when you need to find specific information
        from the uploaded documents.

        Args:
            query: The search query string
        """
        nonlocal calls_made
        if max_calls is not None and calls_made >= max_calls:
            logger.info("search_documents_budget_exhausted", **query_log_fields(query))
            return SEARCH_BUDGET_EXHAUSTED
        calls_made += 1
        search_query = SearchQuery(
            query=query,
            top_k=top_k,
            namespace_prefix=namespace_prefix,
        )
        logger.info(
            "search_documents_called",
            **query_log_fields(query),
            top_k=top_k,
            namespace_prefix=namespace_prefix,
        )
        results = await search.search(search_query)
        if not results:
            logger.info("search_documents_no_results", **query_log_fields(query))
            return SEARCH_NO_RESULTS

        logger.info(
            "search_documents_found", **query_log_fields(query), count=len(results)
        )

        formatted_results = []
        for i, result in enumerate(results, 1):
            snippet = result.content[:2000].strip()
            formatted_results.append(f"[{i}] {snippet}... (Score: {result.score:.3f})")

        return "\n\n".join(formatted_results)

    return _search_documents
