"""Both nginx configs let a GrokBot cover upload reach the backend.

Gherkin: tests/features/autopilot_grok_cover_ae0418.feature
  Scenario: nginx lets a 5 MB cover through to the backend

nginx's default ``client_max_body_size`` is 1 MB: without its own location a
normal 2-3 MB cover gets nginx's HTML 413 before the backend sees it. There is
no nginx binary in CI, so the configs are checked as text.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONFIGS = ("nginx/nginx.conf", "nginx/nginx.conf.ssl")
_ASSETS_LOCATION = "location = /api/autopilot/assets"
_API_LOCATION = "location /api/"
_BODY_SIZE = "client_max_body_size 6m;"
_PROXY_PASS = "proxy_pass http://backend/api/autopilot/assets;"
_HEADER = re.compile(r"^\s*proxy_set_header .*;$", re.MULTILINE)


def _block(config: str, location: str) -> str | None:
    """The body of ``location { ... }``, or None when it is absent."""
    start = config.find(location + " {")
    if start < 0:
        return None
    end = config.find("\n        }", start)
    return config[start:end]


def _upload_problems(config: str) -> list[str]:
    """Why ``config`` would block a cover upload; empty when it is fine."""
    assets = _block(config, _ASSETS_LOCATION)
    if assets is None:
        return ["no /api/autopilot/assets location"]
    problems = [
        f"missing {line}" for line in (_BODY_SIZE, _PROXY_PASS) if line not in assets
    ]
    api = _block(config, _API_LOCATION) or ""
    if set(_HEADER.findall(api)) != set(_HEADER.findall(assets)):
        problems.append("proxy headers differ from /api/")
    return problems


@pytest.mark.unit
@pytest.mark.parametrize("name", _CONFIGS)
def test_config_has_the_cover_upload_location(name: str) -> None:
    config = (_REPO_ROOT / name).read_text(encoding="utf-8")
    assert _upload_problems(config) == []


@pytest.mark.unit
def test_check_fires_on_a_config_without_the_location() -> None:
    config = (_REPO_ROOT / _CONFIGS[0]).read_text(encoding="utf-8")
    seeded = config.replace(_ASSETS_LOCATION, "location = /api/other")
    assert _upload_problems(seeded) == ["no /api/autopilot/assets location"]


@pytest.mark.unit
def test_check_fires_on_the_default_body_size() -> None:
    config = (_REPO_ROOT / _CONFIGS[1]).read_text(encoding="utf-8")
    seeded = config.replace(_BODY_SIZE, "")
    assert _upload_problems(seeded) == [f"missing {_BODY_SIZE}"]


@pytest.mark.unit
def test_check_fires_on_drifted_proxy_headers() -> None:
    config = (_REPO_ROOT / _CONFIGS[0]).read_text(encoding="utf-8")
    start = config.index(_ASSETS_LOCATION)
    head, tail = config[:start], config[start:]
    line = "            proxy_set_header X-Forwarded-Host $host;\n"
    seeded = head + tail.replace(line, "", 1)
    assert _upload_problems(seeded) == ["proxy headers differ from /api/"]
