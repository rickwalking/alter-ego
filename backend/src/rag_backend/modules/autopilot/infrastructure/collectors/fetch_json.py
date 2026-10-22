"""GET a URL and parse the JSON body, raising ``UpstreamError`` on any failure."""

from __future__ import annotations

from rag_backend.modules.autopilot.infrastructure.collectors.coerce import loads_json
from rag_backend.modules.autopilot.infrastructure.collectors.errors import UpstreamError
from rag_backend.modules.autopilot.infrastructure.collectors.http_get import (
    HttpGet,
    HttpGetter,
    is_http_success,
)


async def fetch_json(http: HttpGetter, request: HttpGet) -> object:
    """Return the parsed JSON body. A non-2xx status or an unparsable body raises."""
    response = await http.get(request)
    if not is_http_success(response.status_code):
        raise UpstreamError
    parsed = loads_json(response.text)
    if parsed is None:
        raise UpstreamError
    return parsed
