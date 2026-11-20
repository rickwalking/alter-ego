"""One Instagram Graph JSON call: token, URL, deadline and error translation.

Shared by the Reels reader and the Reels publisher. A non-JSON body (a proxy
or outage page) is a transient error, so the caller retries later.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

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

_GET = "GET"
GRAPH_CALL_DEADLINE_SECONDS = 30.0


@dataclass(frozen=True, kw_only=True)
class GraphCall:
    """A path under the Graph host, its query and the method."""

    path: str
    params: dict[str, str]
    method: str = _GET
    deadline: float = GRAPH_CALL_DEADLINE_SECONDS


class GraphJson:
    """Sends one call with the account's token; raises ``InstagramGraphError``."""

    def __init__(
        self, config: MetaInstagramPublisherConfig, client: httpx.AsyncClient
    ) -> None:
        self._config = config
        self._client = client

    @property
    def ig_user_id(self) -> str:
        """The configured account."""
        return self._config.ig_user_id

    async def call(self, call: GraphCall) -> dict[str, object]:
        """The JSON object of a successful answer."""
        token = await self._config.token_provider.get()
        if not token or not self._config.ig_user_id:
            raise RuntimeError(ERR_INSTAGRAM_CREDENTIALS_NOT_CONFIGURED)
        url = self._config.graph_base.rstrip("/") + call.path
        params = {**call.params, COOKIE_ACCESS_TOKEN: token}
        async with asyncio.timeout(call.deadline):
            response = await self._client.request(call.method, url, params=params)
        if not response.is_success:
            raise error_from(response)
        try:
            return json_dict(response)
        except ValueError as exc:
            raise InstagramGraphError(
                status_code=response.status_code,
                error_code=ERR_INSTAGRAM_API_REQUEST_FAILED,
                transient=True,
            ) from exc


def graph_config(settings: Settings) -> MetaInstagramPublisherConfig | None:
    """The account's Graph config, or None without an Instagram user id."""
    if not settings.meta_ig_user_id.strip():
        return None
    return MetaInstagramPublisherConfig(
        ig_user_id=settings.meta_ig_user_id,
        graph_base=settings.meta_ig_graph_base,
        token_provider=token_provider_for(settings),
    )


__all__ = ["GraphCall", "GraphJson", "graph_config"]
