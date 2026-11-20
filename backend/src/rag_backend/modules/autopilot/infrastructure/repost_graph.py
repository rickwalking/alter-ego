"""Graph Reels publish: container, ``status_code``, ``media_publish``, permalink.

Never edits or deletes the original Reel; every call creates or reads the
new one. Errors surface as ``InstagramCallError`` through ``guard_graph``.
"""

from __future__ import annotations

import json

from rag_backend.domain.constants.instagram_publish import (
    ERR_INSTAGRAM_API_REQUEST_FAILED,
)
from rag_backend.infrastructure.external.instagram_graph_error import (
    InstagramGraphError,
)
from rag_backend.modules.autopilot.application.repost_tick_ports import (
    ContainerRequest,
    ContainerState,
)
from rag_backend.modules.autopilot.ig_media_constants import FIELD_FIELDS, FIELD_ID
from rag_backend.modules.autopilot.infrastructure.graph_json import (
    GraphCall,
    GraphJson,
)
from rag_backend.modules.autopilot.infrastructure.instagram_gateway import guard_graph
from rag_backend.modules.autopilot.repost_constants import (
    GRAPH_FALSE,
    GRAPH_FIELD_CAPTION,
    GRAPH_FIELD_COLLABORATORS,
    GRAPH_FIELD_COVER_URL,
    GRAPH_FIELD_CREATION_ID,
    GRAPH_FIELD_MEDIA_TYPE,
    GRAPH_FIELD_PERMALINK,
    GRAPH_FIELD_SHARE_TO_FEED,
    GRAPH_FIELD_STATUS,
    GRAPH_FIELD_STATUS_CODE,
    GRAPH_FIELD_VIDEO_URL,
    GRAPH_MEDIA_TYPE_REELS,
    GRAPH_PATH_MEDIA,
    GRAPH_PATH_MEDIA_PUBLISH,
    GRAPH_PATH_OBJECT,
    GRAPH_TRUE,
)


class GraphReelPublisher:
    """The Reels container flow on the configured account."""

    def __init__(self, graph: GraphJson) -> None:
        self._graph = graph

    async def create(self, container: ContainerRequest) -> str:
        """The new container id."""
        path = GRAPH_PATH_MEDIA.format(ig_user_id=self._graph.ig_user_id)
        call = GraphCall(method="POST", path=path, params=container_params(container))
        return await guard_graph(lambda: self._id(call))

    async def status(self, container_id: str) -> ContainerState:
        """The container's processing state."""
        fields = f"{GRAPH_FIELD_STATUS_CODE},{GRAPH_FIELD_STATUS}"
        call = GraphCall(
            method="GET",
            path=GRAPH_PATH_OBJECT.format(object_id=container_id),
            params={FIELD_FIELDS: fields},
        )
        payload = await guard_graph(lambda: self._graph.call(call))
        return parse_status(payload)

    async def publish(self, container_id: str) -> str:
        """Publish a finished container; the new media id."""
        call = GraphCall(
            method="POST",
            path=GRAPH_PATH_MEDIA_PUBLISH.format(ig_user_id=self._graph.ig_user_id),
            params={GRAPH_FIELD_CREATION_ID: container_id},
        )
        return await guard_graph(lambda: self._id(call))

    async def permalink(self, media_id: str) -> str | None:
        """The new Reel's permalink, if Graph returns one."""
        call = GraphCall(
            method="GET",
            path=GRAPH_PATH_OBJECT.format(object_id=media_id),
            params={FIELD_FIELDS: GRAPH_FIELD_PERMALINK},
        )
        payload = await guard_graph(lambda: self._graph.call(call))
        value = payload.get(GRAPH_FIELD_PERMALINK)
        return value if isinstance(value, str) and value else None

    async def _id(self, call: GraphCall) -> str:
        return _required_id(await self._graph.call(call))


def container_params(container: ContainerRequest) -> dict[str, str]:
    """The ``POST /{ig-user-id}/media`` fields for a Reel."""
    params = {
        GRAPH_FIELD_MEDIA_TYPE: GRAPH_MEDIA_TYPE_REELS,
        GRAPH_FIELD_VIDEO_URL: container.video_url,
        GRAPH_FIELD_CAPTION: container.caption,
        GRAPH_FIELD_SHARE_TO_FEED: GRAPH_TRUE
        if container.share_to_feed
        else GRAPH_FALSE,
    }
    if container.cover_url:
        params[GRAPH_FIELD_COVER_URL] = container.cover_url
    if container.collaborators:
        params[GRAPH_FIELD_COLLABORATORS] = json.dumps(list(container.collaborators))
    return params


def parse_status(payload: dict[str, object]) -> ContainerState:
    """``status_code`` (empty when absent) and the ``status`` detail."""
    code = payload.get(GRAPH_FIELD_STATUS_CODE)
    detail = payload.get(GRAPH_FIELD_STATUS)
    return ContainerState(
        code=code if isinstance(code, str) else "",
        detail=detail if isinstance(detail, str) and detail else None,
    )


def _required_id(payload: dict[str, object]) -> str:
    value = payload.get(FIELD_ID)
    if not isinstance(value, str) or not value:
        raise InstagramGraphError(
            status_code=0,
            error_code=ERR_INSTAGRAM_API_REQUEST_FAILED,
            transient=False,
        )
    return value


__all__ = [
    "GraphReelPublisher",
    "container_params",
    "parse_status",
]
