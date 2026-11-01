"""Rules for the production proxy settings that make the rate limits per client.

uvicorn takes the client address from ``X-Forwarded-For`` only when the peer is
listed in ``FORWARDED_ALLOW_IPS``; the backend lists loopback and nginx's fixed
address, and nginx sends its own view of the client (the Cloudflare visitor) as
the header. Each check returns the problems it finds, so a seeded wrong config
can prove the check fires.
"""

from __future__ import annotations

import ipaddress
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
DOCKERFILE = REPO_ROOT / "backend" / "Dockerfile"
COMPOSE = REPO_ROOT / "docker-compose.prod.yml"
NGINX_CONFIGS = (
    REPO_ROOT / "nginx" / "nginx.conf",
    REPO_ROOT / "nginx" / "nginx.conf.ssl",
)

ENV_FORWARDED_ALLOW_IPS = "FORWARDED_ALLOW_IPS"
LOOPBACK = "127.0.0.1"
TRUST_ALL = "*"
FLAG_PROXY_HEADERS = "--proxy-headers"
FLAG_NO_PROXY_HEADERS = "--no-proxy-headers"
FLAG_FORWARDED_ALLOW_IPS = "--forwarded-allow-ips"
SERVICE_BACKEND = "backend"
SERVICE_NGINX = "nginx"
NETWORK_DEFAULT = "default"
CLIENT_HEADER = "X-Forwarded-For"
NGINX_CLIENT = "$remote_addr"
NGINX_APPEND = "$proxy_add_x_forwarded_for"
CLOUDFLARE_HEADER = "CF-Connecting-IP"
WIDE_NETWORK_PREFIX = 8

_CMD = re.compile(r"^CMD\s+(?P<args>.+)$", re.MULTILINE)
_XFF = re.compile(
    r"proxy_set_header\s+X-Forwarded-For\s+(?P<value>[^;]+);", re.IGNORECASE
)
_PROXY_PASS = re.compile(r"^\s*proxy_pass\s", re.MULTILINE)
_REAL_IP_FROM = re.compile(r"^\s*set_real_ip_from\s+(?P<cidr>[^;]+);", re.MULTILINE)
_REAL_IP_HEADER = re.compile(r"^\s*real_ip_header\s+(?P<header>[^;]+);", re.MULTILINE)

Document = dict[str, object]


def load_compose(path: Path = COMPOSE) -> Document:
    """The parsed compose file."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _mapping(value: object) -> Document:
    return value if isinstance(value, dict) else {}


def _service(document: Document, name: str) -> Document:
    return _mapping(_mapping(document.get("services")).get(name))


def forwarded_allow_ips(document: Document) -> str:
    """The backend's ``FORWARDED_ALLOW_IPS`` value ('' when unset)."""
    environment = _mapping(_service(document, SERVICE_BACKEND).get("environment"))
    return str(environment.get(ENV_FORWARDED_ALLOW_IPS, ""))


def nginx_address(document: Document) -> str:
    """nginx's fixed address on the default network ('' when not pinned)."""
    networks = _mapping(_service(document, SERVICE_NGINX).get("networks"))
    return str(_mapping(networks.get(NETWORK_DEFAULT)).get("ipv4_address", ""))


def dockerfile_problems(text: str) -> list[str]:
    """Problems with the uvicorn command of the backend image."""
    match = _CMD.search(text)
    if match is None:
        return ["no CMD"]
    args = match.group("args")
    problems: list[str] = []
    if FLAG_PROXY_HEADERS not in args or FLAG_NO_PROXY_HEADERS in args:
        problems.append(f"uvicorn must run with {FLAG_PROXY_HEADERS}")
    if FLAG_FORWARDED_ALLOW_IPS in args:
        problems.append(
            f"{FLAG_FORWARDED_ALLOW_IPS} would override {ENV_FORWARDED_ALLOW_IPS}"
        )
    return problems


def _ipam(document: Document) -> Document:
    network = _mapping(_mapping(document.get("networks")).get(NETWORK_DEFAULT))
    configs = _mapping(network.get("ipam")).get("config")
    if not isinstance(configs, list) or len(configs) != 1:
        return {}
    return _mapping(configs[0])


def _address_problems(nginx: str, ipam: Document) -> list[str]:
    try:
        address = ipaddress.ip_address(nginx)
        subnet = ipaddress.ip_network(str(ipam.get("subnet")))
        dynamic = ipaddress.ip_network(str(ipam.get("ip_range")))
    except ValueError:
        return [
            "the default network must pin a subnet and an ip_range, and nginx an address"
        ]
    if address not in subnet:
        return ["nginx's address is outside the pinned subnet"]
    if address in dynamic:
        return [
            "nginx's address is inside ip_range, so another container could take it"
        ]
    return []


def compose_problems(document: Document) -> list[str]:
    """Problems with who the backend trusts and nginx's fixed address."""
    trusted = [
        host.strip()
        for host in forwarded_allow_ips(document).split(",")
        if host.strip()
    ]
    nginx = nginx_address(document)
    problems = _address_problems(nginx, _ipam(document))
    if not nginx or nginx not in trusted:
        problems.append(f"{ENV_FORWARDED_ALLOW_IPS} must list nginx's fixed address")
    extra = sorted(set(trusted) - {LOOPBACK, nginx})
    if extra:
        problems.append(f"{ENV_FORWARDED_ALLOW_IPS} trusts more than nginx: {extra}")
    return problems


def _real_ip_problems(text: str) -> list[str]:
    problems: list[str] = []
    headers = [m.group("header").strip() for m in _REAL_IP_HEADER.finditer(text)]
    if headers != [CLOUDFLARE_HEADER]:
        problems.append(f"real_ip_header must be {CLOUDFLARE_HEADER}")
    sources = [m.group("cidr").strip() for m in _REAL_IP_FROM.finditer(text)]
    if not sources:
        problems.append("set_real_ip_from must list Cloudflare's ranges")
    for source in sources:
        network = ipaddress.ip_network(source, strict=False)
        if network.prefixlen < WIDE_NETWORK_PREFIX or network.is_private:
            problems.append(f"set_real_ip_from {source} is not a Cloudflare range")
    return problems


def nginx_problems(text: str) -> list[str]:
    """Problems with the client address nginx reads and forwards."""
    problems = _real_ip_problems(text)
    values = [m.group("value").strip() for m in _XFF.finditer(text)]
    if NGINX_APPEND in text or any(value != NGINX_CLIENT for value in values):
        problems.append(
            f"{CLIENT_HEADER} must be {NGINX_CLIENT}, not appended to the client's"
        )
    if len(values) < len(_PROXY_PASS.findall(text)):
        problems.append(f"a proxied location does not set {CLIENT_HEADER}")
    return problems
