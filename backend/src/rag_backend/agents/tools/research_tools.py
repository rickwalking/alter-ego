"""LangChain @tool adapters wrapping the web research service (AE-0249, ADR-0016).

``build_scrape_url_tool`` and ``build_search_web_tool`` are **thin façades**: each
captures a :class:`ResearchTool` Protocol implementation by closure and delegates
to it. They own no business logic and no infrastructure — the Playwright/DDG work
stays in the ``application`` service behind the Protocol, so the agents package
never imports ``rag_backend.application`` (the ``agents -> application`` edge stays
frozen at its AE-0082 baseline).
"""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from rag_backend.agents.tools.constants import (
    DEFAULT_SEARCH_SOURCE_TYPES,
    EMPTY_SEARCH_RESULT,
    SCRAPE_BLOCKED_PREFIX,
    SCRAPE_FAILURE_PREFIX,
    SEARCH_RESULT_TEMPLATE,
    SOURCE_KEY_SNIPPET,
    SOURCE_KEY_TITLE,
    SOURCE_KEY_URL,
)
from rag_backend.agents.tools.url_safety import is_safe_research_url
from rag_backend.domain.protocols import ResearchTool
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()


def _format_sources(sources: list[dict[str, str]]) -> str:
    """Render search hits as a numbered, model-readable source list."""
    if not sources:
        return EMPTY_SEARCH_RESULT
    lines = [
        SEARCH_RESULT_TEMPLATE.format(
            index=index,
            title=source.get(SOURCE_KEY_TITLE, ""),
            url=source.get(SOURCE_KEY_URL, ""),
            snippet=source.get(SOURCE_KEY_SNIPPET, ""),
        )
        for index, source in enumerate(sources, start=1)
    ]
    return "\n\n".join(lines)


def build_scrape_url_tool(research: ResearchTool) -> BaseTool:
    """Return a bound ``scrape_url`` @tool delegating to the research service.

    On an unreachable URL the adapter reports the failure as text instead of
    raising, so the researcher subagent continues without the page (graceful
    degradation, ADR-0249).
    """

    @tool
    async def scrape_url(url: str) -> str:
        """Browse a single URL and return its extracted page text.

        Use this when the user pastes or references a specific web page that
        should inform the carousel content.

        Args:
            url: The absolute URL to browse.
        """
        if not is_safe_research_url(url):
            logger.warning("scrape_url_blocked", url=url)
            return f"{SCRAPE_BLOCKED_PREFIX} {url}: unsafe or non-http(s) target"
        try:
            return await research.scrape_url(url)
        except Exception as exc:
            logger.warning("scrape_url_failed", url=url, error=str(exc))
            return f"{SCRAPE_FAILURE_PREFIX} {url}: {exc}"

    return scrape_url


def build_search_web_tool(research: ResearchTool) -> BaseTool:
    """Return a bound ``search_web`` @tool delegating to the research service."""

    @tool
    async def search_web(query: str) -> str:
        """Search the web for sources relevant to a research query.

        Returns a numbered list of sources with title, URL, and snippet.

        Args:
            query: The search query string.
        """
        sources = await research.search_web(query, list(DEFAULT_SEARCH_SOURCE_TYPES))
        logger.info("search_web_called", query=query, count=len(sources))
        return _format_sources(sources)

    return search_web


__all__ = [
    "build_scrape_url_tool",
    "build_search_web_tool",
]
