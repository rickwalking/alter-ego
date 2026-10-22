"""GitHub repository search for recently created ``topic:llm`` repos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from rag_backend.modules.autopilot.constants import (
    AUTH_BEARER_PREFIX,
    GITHUB_ACCEPT,
    GITHUB_CREATED_PREFIX,
    GITHUB_LOOKBACK_DAYS,
    GITHUB_ORDER_DESC,
    GITHUB_PARAM_ORDER,
    GITHUB_PARAM_Q,
    GITHUB_PARAM_SORT,
    GITHUB_SEARCH_URL,
    GITHUB_SORT_STARS,
    GITHUB_TOPIC_QUERY,
    HEADER_ACCEPT,
    HEADER_AUTHORIZATION,
    SOURCE_GITHUB,
)
from rag_backend.modules.autopilot.domain.signals import (
    CollectWindow,
    Signal,
    SignalDraft,
    SignalSource,
    signal_from,
)
from rag_backend.modules.autopilot.infrastructure.collectors.coerce import (
    as_int,
    as_list,
    as_mapping,
    as_str,
)
from rag_backend.modules.autopilot.infrastructure.collectors.fetch_json import (
    fetch_json,
)
from rag_backend.modules.autopilot.infrastructure.collectors.http_get import (
    HttpGet,
    HttpGetter,
)
from rag_backend.modules.autopilot.infrastructure.collectors.timestamps import (
    parse_timestamp,
)

_KEY_ITEMS = "items"
_KEY_FULL_NAME = "full_name"
_KEY_HTML_URL = "html_url"
_KEY_DESCRIPTION = "description"
_KEY_STARS = "stargazers_count"
_KEY_CREATED = "created_at"
_KEY_OWNER = "owner"
_KEY_LOGIN = "login"


@dataclass(frozen=True, kw_only=True)
class GitHubSearchConfig:
    """HTTP client and the optional token. An empty token sends no Authorization."""

    http: HttpGetter
    token: str


class GitHubSearchCollector:
    """Search repositories created inside the lookback, sorted by stars."""

    def __init__(self, config: GitHubSearchConfig) -> None:
        self._config = config
        self._source = SOURCE_GITHUB

    def source_name(self) -> str:
        """Source id recorded when this collector fails."""
        return self._source

    async def collect(self, window: CollectWindow) -> list[Signal]:
        """Return the first page of matching repositories."""
        parsed = await fetch_json(self._config.http, self._request(window))
        return signals_from_github(parsed)

    def _request(self, window: CollectWindow) -> HttpGet:
        day = (window.as_of.date() - timedelta(days=GITHUB_LOOKBACK_DAYS)).isoformat()
        query = f"{GITHUB_TOPIC_QUERY} {GITHUB_CREATED_PREFIX}{day}"
        return HttpGet(
            url=GITHUB_SEARCH_URL,
            params=(
                (GITHUB_PARAM_Q, query),
                (GITHUB_PARAM_SORT, GITHUB_SORT_STARS),
                (GITHUB_PARAM_ORDER, GITHUB_ORDER_DESC),
            ),
            headers=self._headers(),
        )

    def _headers(self) -> tuple[tuple[str, str], ...]:
        accept = (HEADER_ACCEPT, GITHUB_ACCEPT)
        token = self._config.token.strip()
        if not token:
            return (accept,)
        return (accept, (HEADER_AUTHORIZATION, f"{AUTH_BEARER_PREFIX}{token}"))


def signals_from_github(payload: object) -> list[Signal]:
    """Map a search-repositories body. Items without a URL or a time are skipped."""
    mapping = as_mapping(payload)
    if mapping is None:
        return []
    signals: list[Signal] = []
    for item in as_list(mapping.get(_KEY_ITEMS)):
        signal = _repo(item)
        if signal is not None:
            signals.append(signal)
    return signals


def _repo(item: object) -> Signal | None:
    mapping = as_mapping(item)
    if mapping is None:
        return None
    url = as_str(mapping.get(_KEY_HTML_URL))
    posted_at = parse_timestamp(as_str(mapping.get(_KEY_CREATED)))
    if not url or posted_at is None:
        return None
    title = as_str(mapping.get(_KEY_FULL_NAME))
    return signal_from(
        SignalDraft(
            source=SignalSource.GITHUB,
            url=url,
            title=title,
            text=as_str(mapping.get(_KEY_DESCRIPTION)) or title,
            posted_at=posted_at,
            handle=_login(mapping),
            score_hint=as_int(mapping.get(_KEY_STARS)),
        )
    )


def _login(mapping: dict[str, object]) -> str | None:
    owner = as_mapping(mapping.get(_KEY_OWNER))
    if owner is None:
        return None
    login = as_str(owner.get(_KEY_LOGIN))
    if not login:
        return None
    return login
