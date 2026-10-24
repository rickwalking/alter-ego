"""No CORS on the Grok Bot job-input route (contract section 2.4).

The app-wide ``CORSMiddleware`` answers allowed origins on every route. The
photos linked from an image-edit job are fetched server to server only, so
this middleware, added outside ``CORSMiddleware``, drops every
``Access-Control-*`` response header on ``/api/v1/image-bridge/jobs/*/inputs/*``.
"""

from __future__ import annotations

import re

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_JOB_INPUT_PATH = re.compile(r"^/api/v1/image-bridge/jobs/[^/]+/inputs/[^/]+$")
_CORS_PREFIX = b"access-control-"
_HTTP = "http"


class NoCorsOnJobInputsMiddleware:
    """Strips CORS headers from job-input responses; other routes untouched."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Filter the response start headers on a job-input path."""
        if scope["type"] != _HTTP or not _JOB_INPUT_PATH.match(scope["path"]):
            await self._app(scope, receive, send)
            return

        async def _send(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if not name.lower().startswith(_CORS_PREFIX)
                ]
            await send(message)

        await self._app(scope, receive, _send)


__all__ = ["NoCorsOnJobInputsMiddleware"]
