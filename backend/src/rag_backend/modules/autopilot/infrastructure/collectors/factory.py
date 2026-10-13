"""Wire the free signal collectors. The X resolver defaults to a no-op."""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass

from rag_backend.modules.autopilot.constants import (
    HTTP_TIMEOUT_SECONDS,
    X_QUERY_SPACING_MAX_SECONDS,
    X_QUERY_SPACING_MIN_SECONDS,
    X_RESOLVER_MIRROR,
)
from rag_backend.modules.autopilot.domain.ports import Collector, XPostResolver
from rag_backend.modules.autopilot.infrastructure.collectors.bluesky import (
    BlueskyTrendsCollector,
)
from rag_backend.modules.autopilot.infrastructure.collectors.ddgs_search import (
    DdgsWebSearch,
)
from rag_backend.modules.autopilot.infrastructure.collectors.github_search import (
    GitHubSearchCollector,
    GitHubSearchConfig,
)
from rag_backend.modules.autopilot.infrastructure.collectors.hacker_news import (
    HackerNewsCollector,
)
from rag_backend.modules.autopilot.infrastructure.collectors.http_get import HttpxGetter
from rag_backend.modules.autopilot.infrastructure.collectors.huggingface_papers import (
    HuggingFacePapersCollector,
)
from rag_backend.modules.autopilot.infrastructure.collectors.rss import RssCollector
from rag_backend.modules.autopilot.infrastructure.collectors.x_resolver import (
    MirrorResolver,
    MirrorResolverConfig,
    NoneResolver,
)
from rag_backend.modules.autopilot.infrastructure.collectors.x_web_search import (
    QueryPause,
    SpacingJitter,
    XWebSearchCollector,
    XWebSearchDependencies,
)

_MS_PER_SECOND = 1000


@dataclass(frozen=True, kw_only=True)
class CollectorBuildConfig:
    """Resolver mode, mirror host, and the optional GitHub token."""

    x_resolver: str
    x_mirror_host: str
    github_token: str


class AsyncioPause:
    """Production pause between X search queries."""

    def __init__(self) -> None:
        self.last_seconds = 0.0

    async def pause(self, seconds: float) -> None:
        """Sleep for the jittered gap."""
        self.last_seconds = seconds
        await asyncio.sleep(seconds)


class UniformJitter:
    """Uniform gap in the inclusive 2-5 second range, via ``secrets``."""

    def __init__(self) -> None:
        self.last_seconds = 0.0

    def seconds(self) -> float:
        """Return the next inter-query delay."""
        span = X_QUERY_SPACING_MAX_SECONDS - X_QUERY_SPACING_MIN_SECONDS
        span_ms = int(span * _MS_PER_SECOND)
        extra = secrets.randbelow(span_ms + 1) / _MS_PER_SECOND
        self.last_seconds = X_QUERY_SPACING_MIN_SECONDS + extra
        return self.last_seconds


def build_collectors(config: CollectorBuildConfig) -> tuple[Collector, ...]:
    """Collectors in the bundle's source order."""
    http = HttpxGetter(HTTP_TIMEOUT_SECONDS)
    return (
        _x_collector(config, http),
        HackerNewsCollector(http),
        HuggingFacePapersCollector(http),
        RssCollector(http),
        BlueskyTrendsCollector(http),
        GitHubSearchCollector(GitHubSearchConfig(http=http, token=config.github_token)),
    )


def select_resolver(config: CollectorBuildConfig, http: HttpxGetter) -> XPostResolver:
    """``mirror`` fetches the configured host. Every other value is a no-op."""
    if config.x_resolver == X_RESOLVER_MIRROR:
        return MirrorResolver(
            MirrorResolverConfig(http=http, host=config.x_mirror_host)
        )
    return NoneResolver()


def _x_collector(
    config: CollectorBuildConfig, http: HttpxGetter
) -> XWebSearchCollector:
    deps = XWebSearchDependencies(
        search=DdgsWebSearch(),
        resolver=select_resolver(config, http),
        pause=_pause(),
        jitter=_jitter(),
    )
    return XWebSearchCollector(deps)


def _pause() -> QueryPause:
    return AsyncioPause()


def _jitter() -> SpacingJitter:
    return UniformJitter()
