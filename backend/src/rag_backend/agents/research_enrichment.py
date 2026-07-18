"""Deterministic web-research enrichment for the editorial workflow (AE-0317).

Runs BEFORE source synthesis so every workflow entry point (HTTP route, RAG chat
tool, DeepAgents subagent) researches the same way: user-provided URL sources are
navigated via the shared :class:`ResearchTool` and the topic is searched on
DuckDuckGo, with the hits appended as supplementary ``web_search`` sources.

This is intentionally NOT an agentic loop — ADR-0007 keeps workflow phases
deterministic. The same ``ResearchTool`` powers the chat-side ``researcher``
subagent (AE-0249); here it is driven by plain bounded code: capped scrape count,
bounded concurrency, SSRF guard, and graceful degradation on every failure path
(a dead link or a search outage must never fail a workflow start).
"""

from __future__ import annotations

import asyncio
import re

from rag_backend.agents.input_sanitizer import sanitize_web_content
from rag_backend.agents.tools.constants import (
    DEFAULT_SEARCH_SOURCE_TYPES,
    SOURCE_KEY_SNIPPET,
    SOURCE_KEY_TITLE,
    SOURCE_KEY_URL,
)
from rag_backend.agents.tools.url_safety import is_safe_research_url
from rag_backend.domain.constants.carousel_workflow import SOURCE_TYPE_URL
from rag_backend.domain.constants.research_enrichment import (
    BLOCK_PAGE_MARKERS,
    BLOCK_PAGE_SCAN_CHARS,
    MAX_CONCURRENT_SCRAPES,
    MAX_URL_SOURCES_SCRAPED,
    MAX_WEB_SEARCH_RESULTS,
    SOURCE_TYPE_WEB_SEARCH,
)
from rag_backend.domain.protocols import ResearchEnrichmentParams, ResearchTool
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

# Anchored bare-URL match: same superset rule the legacy RAG-edge scraping used —
# a source is navigable when it is explicitly ``source_type == "url"`` OR its
# content is nothing but an http(s) URL (notes that embed a raw link).
_BARE_URL_RE = re.compile(r"^https?://\S+$")


async def enrich_sources(
    sources: list[dict[str, str]],
    params: ResearchEnrichmentParams,
) -> list[dict[str, str]]:
    """Navigate URL sources and append topic search hits, deterministically."""
    if params.research_tool is None:
        return sources
    enriched = await _scrape_url_sources(sources, params.research_tool)
    enriched.extend(await _search_topic_sources(params.research_tool, params.topic))
    return enriched


def _is_scrapeable(source: dict[str, str]) -> bool:
    content = source.get("content", "")
    if not content:
        return False
    if source.get("source_type") == SOURCE_TYPE_URL:
        return True
    return bool(_BARE_URL_RE.match(content))


def _select_scrape_jobs(sources: list[dict[str, str]]) -> list[int]:
    """Pick the source indexes to navigate: safe URLs only, cap-bounded.

    The SSRF guard runs at selection time so an unsafe URL never consumes a
    slot of the scrape budget (it is skipped with a warning instead).
    """
    budget = MAX_URL_SOURCES_SCRAPED
    jobs: list[int] = []
    for index, source in enumerate(sources):
        if not _is_scrapeable(source):
            continue
        url = source.get("content", "")
        if not is_safe_research_url(url):
            logger.warning("research_url_blocked", url=url)
            continue
        if budget == 0:
            logger.warning("research_url_cap_hit", url=url)
            continue
        budget -= 1
        jobs.append(index)
    return jobs


async def _scrape_url_sources(
    sources: list[dict[str, str]],
    research_tool: ResearchTool,
) -> list[dict[str, str]]:
    """Replace navigable sources' content with scraped page text, bounded."""
    out = [dict(source) for source in sources]
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)
    jobs = _select_scrape_jobs(out)
    results = await asyncio.gather(
        *(_scrape_one(out[i]["content"], research_tool, semaphore) for i in jobs)
    )
    for index, scraped in zip(jobs, results, strict=True):
        if scraped is not None:
            out[index]["content"] = scraped
    return out


def _is_block_page(text: str) -> bool:
    """AE-0321: detect anti-bot/CDN block pages so they never become research."""
    head = text[:BLOCK_PAGE_SCAN_CHARS].lower()
    return any(marker in head for marker in BLOCK_PAGE_MARKERS)


async def _scrape_one(
    url: str,
    research_tool: ResearchTool,
    semaphore: asyncio.Semaphore,
) -> str | None:
    """Scrape one URL; ``None`` keeps the original content (graceful path)."""
    try:
        async with semaphore:
            scraped = await research_tool.scrape_url(url)
    except Exception as exc:
        logger.warning("research_url_scrape_failed", url=url, error=str(exc))
        return None
    sanitized = sanitize_web_content(scraped)
    if _is_block_page(sanitized):
        logger.warning("research_url_block_page", url=url)
        return None
    return sanitized


async def _search_topic_sources(
    research_tool: ResearchTool,
    topic: str,
) -> list[dict[str, str]]:
    """Search the topic and shape the top hits as ``web_search`` sources."""
    try:
        hits = await research_tool.search_web(topic, list(DEFAULT_SEARCH_SOURCE_TYPES))
    except Exception as exc:
        logger.warning("research_search_failed", topic=topic, error=str(exc))
        return []
    sources: list[dict[str, str]] = []
    for hit in hits[:MAX_WEB_SEARCH_RESULTS]:
        snippet = hit.get(SOURCE_KEY_SNIPPET, "")
        if not snippet:
            continue
        sources.append({
            "title": hit.get(SOURCE_KEY_TITLE, ""),
            "content": sanitize_web_content(snippet),
            "source_type": SOURCE_TYPE_WEB_SEARCH,
            "url": hit.get(SOURCE_KEY_URL, ""),
        })
    return sources


__all__ = ["enrich_sources"]
