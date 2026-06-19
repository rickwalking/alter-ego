"""Thin LangChain @tool adapters owned by the agents package (ADR-0016).

These adapters delegate to ``application`` services **via Protocols** only — they
hold no business logic and no infrastructure, so the agent package stays a pure
orchestration façade and never imports ``rag_backend.application``.
"""

from rag_backend.agents.tools.research_tools import (
    build_scrape_url_tool,
    build_search_web_tool,
)

__all__ = [
    "build_scrape_url_tool",
    "build_search_web_tool",
]
