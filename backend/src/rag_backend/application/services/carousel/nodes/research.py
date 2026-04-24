"""Phase 1: research node.

User-provided seed URLs are the authoritative primary sources — they go
in first and get scraped before anything else. DDG search only
supplements them up to 10 sources total, so the carousel content stays
anchored to the user's actual context instead of drifting toward
whatever DDG surfaces for the topic string.
"""

from __future__ import annotations

import asyncio

from rag_backend.domain.models import CarouselProject, ResearchSource, ResearchSourceType
from rag_backend.domain.protocols import CarouselRepository, ResearchTool
from rag_backend.infrastructure.logging import get_logger

logger = get_logger()

MAX_SOURCES = 10
SCRAPE_TOP_N = 5


def classify_source(url: str) -> ResearchSourceType:
    """Infer a `ResearchSourceType` from the URL host."""
    lowered = url.lower()
    if "twitter.com" in lowered or "x.com" in lowered:
        return ResearchSourceType.TWITTER
    if "github.com" in lowered:
        return ResearchSourceType.GITHUB
    return ResearchSourceType.BLOG


async def _scrape_one(research_tool: ResearchTool, url: str) -> str:
    try:
        return await research_tool.scrape_url(url)
    except Exception as exc:
        logger.warning("carousel_scrape_failed", url=url, error=str(exc))
        return ""


async def run_research(
    project: CarouselProject,
    seed_urls: list[str],
    *,
    repo: CarouselRepository,
    research_tool: ResearchTool,
) -> list[ResearchSource]:
    """Gather research sources for a carousel project."""
    sources: list[ResearchSource] = [
        ResearchSource(
            project_id=project.id,
            source_url=url,
            source_type=classify_source(url),
            title=None,
            relevance_score=2.0,
        )
        for url in seed_urls
        if url
    ]

    if len(sources) < MAX_SOURCES:
        query = f"{project.topic} {project.niche}"
        search_results = await research_tool.search_web(
            query=query,
            _source_types=[
                ResearchSourceType.TWITTER,
                ResearchSourceType.BLOG,
                ResearchSourceType.NEWS,
                ResearchSourceType.GITHUB,
            ],
        )
        existing = {s.source_url for s in sources}
        remaining = MAX_SOURCES - len(sources)
        for r in search_results:
            url = r.get("url", "")
            if url and url not in existing:
                sources.append(
                    ResearchSource(
                        project_id=project.id,
                        source_url=url,
                        source_type=ResearchSourceType.BLOG,
                        title=r.get("title"),
                        relevance_score=1.0,
                    )
                )
                existing.add(url)
                if len(sources) - len(seed_urls) >= remaining:
                    break

    scrape_tasks = [_scrape_one(research_tool, s.source_url) for s in sources[:SCRAPE_TOP_N]]
    scrape_results = await asyncio.gather(*scrape_tasks, return_exceptions=True)
    for source, result in zip(sources[:SCRAPE_TOP_N], scrape_results, strict=False):
        if isinstance(result, str) and result:
            source.extracted_content = result

    persisted: list[ResearchSource] = []
    for source in sources:
        persisted.append(await repo.create_research_source(source))
    return persisted
