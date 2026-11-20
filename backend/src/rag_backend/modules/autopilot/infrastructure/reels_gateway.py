"""Graph reads of the account's Reels: the media walk, one media, collaborators.

Same host, user id and token provider as the publisher. Media URLs are read
fresh on every call and are never stored.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from rag_backend.infrastructure.config.settings import Settings
from rag_backend.infrastructure.external.instagram_graph_error import (
    InstagramGraphError,
)
from rag_backend.modules.autopilot.domain.reels import ReelMedia
from rag_backend.modules.autopilot.ig_media_constants import (
    FIELD_AFTER,
    FIELD_CAPTION,
    FIELD_CURSORS,
    FIELD_FIELDS,
    FIELD_ID,
    FIELD_LIMIT,
    FIELD_MEDIA_PRODUCT_TYPE,
    FIELD_PAGING,
    FIELD_PERMALINK,
    FIELD_TIMESTAMP,
    GRAPH_PATH_USER_MEDIA,
    PRODUCT_REELS,
)
from rag_backend.modules.autopilot.infrastructure.graph_json import (
    GraphCall,
    GraphJson,
    graph_config,
)
from rag_backend.modules.autopilot.infrastructure.instagram_gateway import guard_graph
from rag_backend.modules.autopilot.insights_constants import FIELD_DATA
from rag_backend.modules.autopilot.reels_constants import (
    FIELD_MEDIA_URL,
    FIELD_OWNER,
    FIELD_SHORTCODE,
    FIELD_THUMBNAIL_URL,
    MEDIA_FIELDS_ONE,
    REELS_FIELDS,
    REELS_MAX_PAGES,
    REELS_PAGE_DEADLINE_SECONDS,
    REELS_PAGE_SIZE,
    USERNAME_MAX,
)
from rag_backend.modules.autopilot.repost_constants import (
    GRAPH_FIELD_USERNAME,
    GRAPH_PATH_COLLABORATORS,
    GRAPH_PATH_OBJECT,
)

_CLIENT_ERROR_MIN = 400
_SERVER_ERROR_MIN = 500


class GraphReelGateway:
    """``ReelGateway`` over the Instagram Graph API."""

    def __init__(self, graph: GraphJson) -> None:
        self._graph = graph

    @property
    def ig_user_id(self) -> str:
        """The account the gateway reads."""
        return self._graph.ig_user_id

    async def list_reels(self, since: datetime) -> list[ReelMedia]:
        """Reels newest first until ``since`` or the page cap."""
        return await guard_graph(lambda: self._walk(since))

    async def reel(self, media_id: str) -> ReelMedia | None:
        """One of the account's media, or None for a foreign or unknown id."""
        if not media_id.isdigit():
            return None
        return await guard_graph(lambda: self._reel(media_id))

    async def collaborators(self, media_id: str) -> tuple[str, ...]:
        """Collaborator usernames; a 4xx refusal reads as none."""
        return await guard_graph(lambda: self._collaborators(media_id))

    async def _reel(self, media_id: str) -> ReelMedia | None:
        path = GRAPH_PATH_OBJECT.format(object_id=media_id)
        payload = await self._found(path, {FIELD_FIELDS: MEDIA_FIELDS_ONE})
        if payload is None or not _owned(payload, self.ig_user_id):
            return None
        return parse_reel(payload)

    async def _collaborators(self, media_id: str) -> tuple[str, ...]:
        path = GRAPH_PATH_COLLABORATORS.format(media_id=media_id)
        payload = await self._found(path, {})
        return () if payload is None else parse_collaborators(payload)

    async def _found(
        self, path: str, params: dict[str, str]
    ) -> dict[str, object] | None:
        try:
            return await self._get(path, params)
        except InstagramGraphError as exc:
            if _not_found(exc):
                return None
            raise

    async def _walk(self, since: datetime) -> list[ReelMedia]:
        found: list[ReelMedia] = []
        after: str | None = None
        path = GRAPH_PATH_USER_MEDIA.format(ig_user_id=self.ig_user_id)
        for _page in range(REELS_MAX_PAGES):
            payload = await self._get(path, _page_params(after))
            items = parse_reels_page(payload)
            found.extend(item for item in items if item.posted_at >= since)
            after = _cursor(payload)
            if after is None or any(item.posted_at < since for item in items):
                return found
        return found

    async def _get(self, path: str, params: dict[str, str]) -> dict[str, object]:
        call = GraphCall(path=path, params=params, deadline=REELS_PAGE_DEADLINE_SECONDS)
        return await self._graph.call(call)


def build_reel_gateway(
    settings: Settings, client: httpx.AsyncClient
) -> GraphReelGateway | None:
    """The Reels reader, or None when no Instagram user id is configured."""
    config = graph_config(settings)
    if config is None:
        return None
    return GraphReelGateway(GraphJson(config, client))


def parse_reels_page(payload: dict[str, object]) -> list[ReelMedia]:
    """Every Reel of one media page; other media and odd rows are skipped."""
    data = payload.get(FIELD_DATA)
    if not isinstance(data, list):
        return []
    parsed = (parse_reel(item) for item in data if isinstance(item, dict))
    return [
        item
        for item in parsed
        if item is not None and item.product_type == PRODUCT_REELS
    ]


def parse_reel(item: dict[str, object]) -> ReelMedia | None:
    """One media object, or None without a numeric id and a timestamp."""
    media_id = item.get(FIELD_ID)
    posted_at = _posted(item.get(FIELD_TIMESTAMP))
    if not isinstance(media_id, str) or not media_id.isdigit() or posted_at is None:
        return None
    return ReelMedia(
        media_id=media_id,
        shortcode=_text(item.get(FIELD_SHORTCODE)),
        permalink=_text(item.get(FIELD_PERMALINK)),
        product_type=_text(item.get(FIELD_MEDIA_PRODUCT_TYPE)),
        posted_at=posted_at,
        caption=_text(item.get(FIELD_CAPTION)),
        video_url=_text(item.get(FIELD_MEDIA_URL)),
        thumbnail_url=_text(item.get(FIELD_THUMBNAIL_URL)),
    )


def parse_collaborators(payload: dict[str, object]) -> tuple[str, ...]:
    """Usernames from a collaborators edge body."""
    data = payload.get(FIELD_DATA)
    if not isinstance(data, list):
        return ()
    names = (item.get(GRAPH_FIELD_USERNAME) for item in data if isinstance(item, dict))
    return tuple(
        name
        for name in names
        if isinstance(name, str) and 0 < len(name) <= USERNAME_MAX
    )


def _owned(payload: dict[str, object], ig_user_id: str) -> bool:
    owner = payload.get(FIELD_OWNER)
    if not isinstance(owner, dict):
        return True
    return str(owner.get(FIELD_ID, "")) == ig_user_id


def _not_found(exc: InstagramGraphError) -> bool:
    client_error = _CLIENT_ERROR_MIN <= exc.status_code < _SERVER_ERROR_MIN
    return client_error and not exc.transient


def _page_params(after: str | None) -> dict[str, str]:
    params = {FIELD_FIELDS: REELS_FIELDS, FIELD_LIMIT: str(REELS_PAGE_SIZE)}
    if after is not None:
        params[FIELD_AFTER] = after
    return params


def _cursor(payload: dict[str, object]) -> str | None:
    paging = payload.get(FIELD_PAGING)
    cursors = paging.get(FIELD_CURSORS) if isinstance(paging, dict) else None
    after = cursors.get(FIELD_AFTER) if isinstance(cursors, dict) else None
    return after if isinstance(after, str) and after else None


def _posted(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


__all__ = [
    "GraphReelGateway",
    "build_reel_gateway",
    "parse_collaborators",
    "parse_reel",
    "parse_reels_page",
]
