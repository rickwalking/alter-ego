"""Both nginx configs let a 200 MB source video upload reach the backend.

Gherkin: tests/features/autopilot_repost_source_video_ae0641.feature
  Scenario: nginx lets a 200 MB upload through to the backend

There is no nginx binary in CI, so the configs are checked as text.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONFIGS = ("nginx/nginx.conf", "nginx/nginx.conf.ssl")
_LOCATION = "location = /api/autopilot/assets/video"
_API_LOCATION = "location /api/"
_REQUIRED = (
    "client_max_body_size 210m;",
    "proxy_request_buffering off;",
    "proxy_pass http://backend/api/autopilot/assets/video;",
)
_HEADER = re.compile(r"^\s*proxy_set_header .*;$", re.MULTILINE)


def _block(config: str, location: str) -> str | None:
    start = config.find(location + " {")
    if start < 0:
        return None
    return config[start : config.find("\n        }", start)]


def _problems(config: str) -> list[str]:
    block = _block(config, _LOCATION)
    if block is None:
        return ["no /api/autopilot/assets/video location"]
    problems = [f"missing {line}" for line in _REQUIRED if line not in block]
    api = _block(config, _API_LOCATION) or ""
    if set(_HEADER.findall(api)) != set(_HEADER.findall(block)):
        problems.append("proxy headers differ from /api/")
    return problems


# Scenario: nginx lets a 200 MB upload through to the backend
@pytest.mark.unit
@pytest.mark.parametrize("name", _CONFIGS)
def test_config_has_the_source_video_location(name: str) -> None:
    config = (_REPO_ROOT / name).read_text(encoding="utf-8")
    assert _problems(config) == []


@pytest.mark.unit
def test_check_fires_without_the_location() -> None:
    config = (_REPO_ROOT / _CONFIGS[0]).read_text(encoding="utf-8")
    seeded = config.replace(_LOCATION, "location = /api/other")
    assert _problems(seeded) == ["no /api/autopilot/assets/video location"]


@pytest.mark.unit
def test_check_fires_on_a_small_body_limit() -> None:
    config = (_REPO_ROOT / _CONFIGS[1]).read_text(encoding="utf-8")
    seeded = config.replace("client_max_body_size 210m;", "client_max_body_size 6m;")
    assert _problems(seeded) == ["missing client_max_body_size 210m;"]


@pytest.mark.unit
def test_check_fires_on_drifted_proxy_headers() -> None:
    config = (_REPO_ROOT / _CONFIGS[0]).read_text(encoding="utf-8")
    start = config.index(_LOCATION)
    head, tail = config[:start], config[start:]
    line = "            proxy_set_header X-Forwarded-Host $host;\n"
    assert _problems(head + tail.replace(line, "", 1)) == [
        "proxy headers differ from /api/"
    ]
