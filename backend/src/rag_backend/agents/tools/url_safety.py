"""SSRF boundary guard for the research ``scrape_url`` @tool.

The researcher subagent is LLM-driven and autopilot feeds third-party story
links, so every URL handed to the scraper is untrusted. The rules live in
``rag_backend.domain.url_safety`` so the Playwright scraper (``application``)
re-checks each redirect hop with the same code:

- only ``http(s)``;
- no known-internal host (loopback alias, metadata service, docker-compose
  service names) and no single-label host;
- every DNS answer must be globally routable (QA r1 S-W1).

Imports only the domain, so the ``agents -> application`` edge stays frozen at
its baseline.
"""

from __future__ import annotations

from rag_backend.domain.url_safety import is_safe_url_syntax, is_safe_url_target


def is_safe_research_url(url: str) -> bool:
    """Return True when ``url`` passes the checks that need no DNS lookup."""
    return is_safe_url_syntax(url)


async def is_safe_research_target(url: str) -> bool:
    """Return True when ``url`` is safe and its host resolves only to public IPs."""
    return await is_safe_url_target(url)


__all__ = ["is_safe_research_target", "is_safe_research_url"]
