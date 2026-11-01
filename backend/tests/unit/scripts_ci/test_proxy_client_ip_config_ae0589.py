"""The production proxy config that makes the rate limits per client.

Feature: backend/tests/features/rate_limit_client_ip_ae0589.feature
"""

from __future__ import annotations

import copy

import pytest

from tests.unit.scripts_ci.proxy_client_ip_rules import (
    DOCKERFILE,
    NGINX_CONFIGS,
    Document,
    compose_problems,
    dockerfile_problems,
    load_compose,
    nginx_problems,
)

GOOD_CMD = 'CMD ["uvicorn", "app", "--port", "8000", "--proxy-headers"]\n'
NGINX_ADDRESS = "172.18.200.10"
GOOD_NGINX = """
    set_real_ip_from 173.245.48.0/20;
    real_ip_header CF-Connecting-IP;
    location /api/ {
        proxy_pass http://backend/api/;
        proxy_set_header X-Forwarded-For $remote_addr;
    }
"""


def _good_compose() -> Document:
    return {
        "services": {
            "backend": {
                "environment": {"FORWARDED_ALLOW_IPS": f"127.0.0.1,{NGINX_ADDRESS}"}
            },
            "nginx": {"networks": {"default": {"ipv4_address": NGINX_ADDRESS}}},
        },
        "networks": {
            "default": {
                "ipam": {
                    "config": [{"subnet": "172.18.0.0/16", "ip_range": "172.18.0.0/17"}]
                }
            }
        },
    }


def _with(path: tuple[str, ...], value: object) -> Document:
    document = copy.deepcopy(_good_compose())
    node: dict[str, object] = document
    for key in path[:-1]:
        child = node[key]
        assert isinstance(child, dict)
        node = child
    node[path[-1]] = value
    return document


_TRUSTED = ("services", "backend", "environment", "FORWARDED_ALLOW_IPS")
_NGINX_IP = ("services", "nginx", "networks", "default", "ipv4_address")
_IPAM = ("networks", "default", "ipam", "config")


# Scenario: The production config trusts forwarded addresses from nginx only
def test_production_config_trusts_nginx_only() -> None:
    """The real Dockerfile, compose file and both nginx configs pass every rule."""
    assert dockerfile_problems(DOCKERFILE.read_text(encoding="utf-8")) == []
    assert compose_problems(load_compose()) == []
    for config in NGINX_CONFIGS:
        assert nginx_problems(config.read_text(encoding="utf-8")) == [], config.name


def test_seeded_good_config_passes() -> None:
    """The seeded baseline is clean, so each seeded mistake below is the only one."""
    assert dockerfile_problems(GOOD_CMD) == []
    assert compose_problems(_good_compose()) == []
    assert nginx_problems(GOOD_NGINX) == []


# Scenario: A wrong proxy config is reported
@pytest.mark.parametrize(
    "command",
    [
        'CMD ["uvicorn", "app", "--port", "8000"]\n',
        'CMD ["uvicorn", "app", "--no-proxy-headers"]\n',
        'CMD ["uvicorn", "app", "--proxy-headers", "--forwarded-allow-ips", "*"]\n',
        'ENTRYPOINT ["uvicorn"]\n',
    ],
)
def test_wrong_uvicorn_command_is_reported(command: str) -> None:
    """Missing or disabled proxy headers, or a CLI override of the env, fail."""
    assert dockerfile_problems(command) != []


# Scenario: A wrong proxy config is reported
@pytest.mark.parametrize(
    ("path", "value"),
    [
        (_TRUSTED, "*"),
        (_TRUSTED, "127.0.0.1"),
        (_TRUSTED, f"127.0.0.1,{NGINX_ADDRESS},172.18.0.0/16"),
        (_TRUSTED, f"{NGINX_ADDRESS},172.18.0.8"),
        (_NGINX_IP, ""),
        (_NGINX_IP, "172.18.0.10"),
        (_NGINX_IP, "10.0.0.10"),
        (_IPAM, []),
    ],
)
def test_wrong_compose_trust_is_reported(path: tuple[str, ...], value: object) -> None:
    """Trusting everyone, a subnet or another container, or an unpinned nginx, fail."""
    assert compose_problems(_with(path, value)) != []


def test_unpinned_nginx_with_matching_trust_is_reported() -> None:
    """nginx without a fixed address is reported even if the env names some address."""
    document = _with(("services", "nginx"), {})
    assert compose_problems(document) != []


# Scenario: A wrong proxy config is reported
@pytest.mark.parametrize(
    "config",
    [
        GOOD_NGINX.replace("$remote_addr;", "$proxy_add_x_forwarded_for;"),
        GOOD_NGINX.replace("$remote_addr;", "$http_x_forwarded_for;"),
        GOOD_NGINX.replace(
            "        proxy_set_header X-Forwarded-For $remote_addr;\n", ""
        ),
        GOOD_NGINX.replace("    real_ip_header CF-Connecting-IP;\n", ""),
        GOOD_NGINX.replace("CF-Connecting-IP", "X-Forwarded-For"),
        GOOD_NGINX.replace("    set_real_ip_from 173.245.48.0/20;\n", ""),
        GOOD_NGINX.replace("173.245.48.0/20", "0.0.0.0/0"),
        GOOD_NGINX.replace("173.245.48.0/20", "172.16.0.0/12"),
    ],
)
def test_wrong_nginx_client_header_is_reported(config: str) -> None:
    """An appended or client-copied header, or a trust-all real-IP source, fail."""
    assert nginx_problems(config) != []
