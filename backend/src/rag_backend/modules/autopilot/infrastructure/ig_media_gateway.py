"""Graph ``/{ig-user-id}/media`` reader for the autopilot insights route.

Same host, user id and token provider as the publisher. The walk stops at
``since`` or after four pages. Stories are skipped. The caption stored later
is an excerpt; this reader never keeps a media URL.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from rag_backend.domain.constants import COOKIE_ACCESS_TOKEN
from rag_backend.domain.constants.instagram_publish import (
    ERR_INSTAGRAM_API_REQUEST_FAILED,
    ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED,
)
from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.instagram_graph_error import (
    InstagramGraphError,
)
from rag_backend.infrastructure.external.instagram_graph_payloads import (
    error_from,
    json_dict,
)
from rag_backend.infrastructure.external.instagram_publisher_factory import (
    token_provider_for,
)
from rag_backend.infrastructure.external.meta_instagram_publisher import (
    MetaInstagramPublisherConfig,
)
from rag_backend.modules.autopilot.domain.ig_media import (
    IgMedia,
    MediaListCommand,
    MediaListResult,
)
from rag_backend.modules.autopilot.domain.topic_text import strip_controls
from rag_backend.modules.autopilot.ig_media_constants import (
    CAPTION_EXCERPT_LENGTH,
    FIELD_AFTER,
    FIELD_CAPTION,
    FIELD_COMMENTS_COUNT,
    FIELD_CURSORS,
    FIELD_FIELDS,
    FIELD_ID,
    FIELD_LIKE_COUNT,
    FIELD_LIMIT,
    FIELD_MEDIA_PRODUCT_TYPE,
    FIELD_MEDIA_TYPE,
    FIELD_PAGING,
    FIELD_PERMALINK,
    FIELD_TIMESTAMP,
    GRAPH_PATH_USER_MEDIA,
    IG_MEDIA_MAX_PAGES,
    IG_MEDIA_PAGE_SIZE,
    MEDIA_FIELDS,
    MEDIA_TYPES,
    PRODUCT_STORY,
)
from rag_backend.modules.autopilot.infrastructure.instagram_gateway import guard_graph
from rag_backend.modules.autopilot.insights_constants import FIELD_DATA

_PAGE_DEADLINE_SECONDS = 10.0


class GraphMediaListGateway:
    """``MediaListGateway`` over the Instagram Graph media edge."""

    def __init__(
        self, config: MetaInstagramPublisherConfig, client: httpx.AsyncClient
    ) -> None:
        self._config = config
        self._client = client

    async def list_media(self, command: MediaListCommand) -> MediaListResult:
        """Newest first until ``since`` or the page cap."""
        return await guard_graph(lambda: self._walk(command))

    async def _walk(self, command: MediaListCommand) -> MediaListResult:
        collected: list[IgMedia] = []
        after: str | None = None
        for _page in range(IG_MEDIA_MAX_PAGES):
            page = await self._page(after)
            kept, stop = _keep(page.items, command.since)
            collected.extend(kept)
            if stop or page.after is None:
                return MediaListResult(items=tuple(collected), truncated=False)
            after = page.after
        return MediaListResult(items=tuple(collected), truncated=True)

    async def _page(self, after: str | None) -> _Page:
        token = await self._config.token_provider.get()
        if not token or not self._config.ig_user_id:
            raise RuntimeError(ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED)
        url = self._config.graph_base.rstrip("/") + GRAPH_PATH_USER_MEDIA.format(
            ig_user_id=self._config.ig_user_id
        )
        params = _params(token, after)
        async with asyncio.timeout(_PAGE_DEADLINE_SECONDS):
            response = await self._client.get(url, params=params)
        return _page_from(response)


def build_ig_media_gateway(
    settings: Settings, client: httpx.AsyncClient
) -> GraphMediaListGateway | None:
    """The media-list reader, or None when no Instagram user id is configured."""
    if not settings.meta_ig_user_id.strip():
        return None
    return GraphMediaListGateway(
        MetaInstagramPublisherConfig(
            ig_user_id=settings.meta_ig_user_id,
            graph_base=settings.meta_ig_graph_base,
            token_provider=token_provider_for(settings),
        ),
        client,
    )


def parse_media_page(
    payload: dict[str, object],
) -> tuple[tuple[IgMedia, ...], str | None]:
    """Media rows and the next cursor. Odd entries are skipped."""
    data = payload.get(FIELD_DATA)
    items = _items(data) if isinstance(data, list) else ()
    return items, _cursor(payload)


def _params(token: str, after: str | None) -> dict[str, str]:
    params = {
        FIELD_FIELDS: MEDIA_FIELDS,
        FIELD_LIMIT: str(IG_MEDIA_PAGE_SIZE),
        COOKIE_ACCESS_TOKEN: token,
    }
    if after is not None:
        params[FIELD_AFTER] = after
    return params


def _page_from(response: httpx.Response) -> _Page:
    try:
        if not response.is_success:
            raise error_from(response)
        items, after = parse_media_page(json_dict(response))
    except ValueError as exc:
        raise InstagramGraphError(
            status_code=response.status_code,
            error_code=ERR_INSTAGRAM_API_REQUEST_FAILED,
            transient=True,
        ) from exc
    return _Page(items=items, after=after)


def _items(data: list[object]) -> tuple[IgMedia, ...]:
    parsed = [_media(item) for item in data if isinstance(item, dict)]
    return tuple(item for item in parsed if item is not None)


def _media(item: dict[str, object]) -> IgMedia | None:
    media_id = item.get(FIELD_ID)
    media_type = item.get(FIELD_MEDIA_TYPE)
    posted_at = _posted(item.get(FIELD_TIMESTAMP))
    product = _text(item.get(FIELD_MEDIA_PRODUCT_TYPE))
    if not isinstance(media_id, str) or not media_id.isdigit():
        return None
    if not isinstance(media_type, str) or media_type not in MEDIA_TYPES:
        return None
    if posted_at is None or product == PRODUCT_STORY:
        return None
    return IgMedia(
        media_id=media_id,
        media_type=media_type,
        media_product_type=product,
        permalink=_text(item.get(FIELD_PERMALINK)),
        caption_excerpt=_excerpt(item.get(FIELD_CAPTION)),
        posted_at=posted_at,
        like_count=_count(item.get(FIELD_LIKE_COUNT)),
        comments_count=_count(item.get(FIELD_COMMENTS_COUNT)),
    )


def _keep(items: Sequence[IgMedia], since: datetime) -> tuple[list[IgMedia], bool]:
    kept: list[IgMedia] = []
    for item in items:
        if item.posted_at < since:
            return kept, True
        kept.append(item)
    return kept, False


def _cursor(payload: dict[str, object]) -> str | None:
    paging = payload.get(FIELD_PAGING)
    if not isinstance(paging, dict):
        return None
    cursors = paging.get(FIELD_CURSORS)
    if not isinstance(cursors, dict):
        return None
    after = cursors.get(FIELD_AFTER)
    if not isinstance(after, str) or after == "":
        return None
    return after


def _posted(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _excerpt(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = strip_controls(value)
    if cleaned == "":
        return None
    return cleaned[:CAPTION_EXCERPT_LENGTH]


def _text(value: object) -> str | None:
    if not isinstance(value, str) or value == "":
        return None
    return value


def _count(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


@dataclass(frozen=True, kw_only=True)
class _Page:
    items: tuple[IgMedia, ...]
    after: str | None


__all__ = ["GraphMediaListGateway", "build_ig_media_gateway", "parse_media_page"]
