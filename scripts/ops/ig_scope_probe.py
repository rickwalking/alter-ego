#!/usr/bin/env python3
"""Check that the Instagram token can read media insights.

Reads ``META_IG_ACCESS_TOKEN`` and ``IG_MEDIA_ID`` from the environment.
Prints ``ok``, ``missing_scope``, ``missing_env`` or ``transient``. Never
prints the token or the response body.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_TOKEN = "META_IG_ACCESS_TOKEN"
_MEDIA = "IG_MEDIA_ID"
_METRIC = "reach,saved"
_PERMISSION_CODES = frozenset({"10", "200"})
_OK = "ok"
_MISSING_SCOPE = "missing_scope"
_MISSING_ENV = "missing_env"
_TRANSIENT = "transient"
_EXIT_OK = 0
_EXIT_SCOPE = 1
_EXIT_USAGE = 2


def main() -> int:
    """One insights read. The token stays in the query string and off stdout."""
    token = os.environ.get(_TOKEN, "").strip()
    media_id = os.environ.get(_MEDIA, "").strip()
    if not token or not media_id:
        print(_MISSING_ENV)
        return _EXIT_USAGE
    url = _url(media_id, token)
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            body = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        body = exc.read()
        status = exc.code
    except urllib.error.URLError:
        print(_TRANSIENT)
        return _EXIT_SCOPE
    return _report(status, body)


def _url(media_id: str, token: str) -> str:
    query = urllib.parse.urlencode({"metric": _METRIC, "access_token": token})
    return f"{_graph_host()}/{media_id}/insights?{query}"


def _graph_host() -> str:
    src = Path(__file__).resolve().parents[2] / "backend" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from rag_backend.domain.constants.instagram_publish import GRAPH_HOST_INSTAGRAM

    return GRAPH_HOST_INSTAGRAM


def _report(status: int, body: bytes) -> int:
    if status == 200:
        print(_OK)
        return _EXIT_OK
    code = _error_code(body)
    if code in _PERMISSION_CODES:
        print(_MISSING_SCOPE)
        return _EXIT_SCOPE
    print(_TRANSIENT)
    return _EXIT_SCOPE


def _error_code(body: bytes) -> str:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ""
    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        return ""
    code = error.get("code")
    return "" if code is None else str(code)


if __name__ == "__main__":
    sys.exit(main())
