"""GET ``graph.instagram.com/refresh_access_token``. The token is not logged."""

from __future__ import annotations

import httpx

from rag_backend.modules.autopilot.credential_constants import (
    GRANT_TYPE_IG_REFRESH,
    GRAPH_ACCESS_PARAM,
    IG_REFRESH_TIMEOUT_SECONDS,
    IG_REFRESH_URL,
    PARAM_GRANT_TYPE,
)
from rag_backend.modules.autopilot.domain.credential_ports import (
    RefreshGrant,
    RefreshRequest,
    TokenRefreshError,
)
from rag_backend.modules.autopilot.domain.token_refresh import parse_refresh_response


class HttpxInstagramTokenClient:
    """One-shot client. Redirects and environment proxies stay off."""

    def __init__(self) -> None:
        self._timeout = IG_REFRESH_TIMEOUT_SECONDS

    async def refresh(self, request: RefreshRequest) -> RefreshGrant:
        """Exchange the current credential. Failures omit the secret."""
        try:
            body = await _get(request.token, self._timeout)
        except httpx.HTTPError:
            raise TokenRefreshError(status_code=0, error_code=None) from None
        return parse_refresh_response(body.status_code, body.text)


async def _get(token: str, timeout: float) -> httpx.Response:
    params = {
        PARAM_GRANT_TYPE: GRANT_TYPE_IG_REFRESH,
        GRAPH_ACCESS_PARAM: token,
    }
    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
        return await client.get(
            IG_REFRESH_URL,
            params=params,
            follow_redirects=False,
        )
