"""Memory caps of the production containers.

Feature: backend/tests/features/compose_memory_caps_ae0521.feature
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
COMPOSE = REPO_ROOT / "docker-compose.prod.yml"
ONE_SHOT = "no"
MEMORY_VALUE = re.compile(r"^(?P<amount>\d+)(?P<unit>[kKmMgG])$")
UNIT_MIB = {"k": 1 / 1024, "m": 1, "g": 1024}
MEASURED_HD_RUN_PEAK_MIB = 1222
HEADROOM = 1.3

Service = dict[str, object]


def _services() -> dict[str, Service]:
    document = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    services = document["services"]
    assert isinstance(services, dict)
    return services


def _mib(value: str) -> float:
    match = MEMORY_VALUE.match(value)
    assert match, f"unparsable memory value: {value}"
    return int(match.group("amount")) * UNIT_MIB[match.group("unit").lower()]


def _memory(service: Service, kind: str) -> float | None:
    deploy = service.get("deploy")
    if not isinstance(deploy, dict):
        return None
    resources = deploy.get("resources")
    if not isinstance(resources, dict):
        return None
    section = resources.get(kind)
    if not isinstance(section, dict) or "memory" not in section:
        return None
    return _mib(str(section["memory"]))


def _limit(service: Service) -> float | None:
    if "mem_limit" in service:
        return _mib(str(service["mem_limit"]))
    return _memory(service, "limits")


def _uncapped(services: dict[str, Service]) -> list[str]:
    return sorted(
        name
        for name, service in services.items()
        if service.get("restart") != ONE_SHOT and _limit(service) is None
    )


def test_every_long_running_service_has_a_memory_limit() -> None:
    """Scenario: Every long-running service has a memory limit"""
    services = _services()
    long_running = [n for n, s in services.items() if s.get("restart") != ONE_SHOT]
    assert "backend" in long_running
    assert _uncapped(services) == []


def test_a_service_without_a_memory_limit_is_reported() -> None:
    """Scenario: A service without a memory limit is reported"""
    seeded: dict[str, Service] = {
        "web": {"restart": "unless-stopped"},
        "worker": {"restart": "always"},
        "sidecar": {},
        "capped": {"restart": "unless-stopped", "mem_limit": "1g"},
        "one-shot": {"restart": ONE_SHOT},
    }
    assert _uncapped(seeded) == ["sidecar", "web", "worker"]


def test_reservations_never_exceed_their_limits() -> None:
    """Scenario: Reservations never exceed their limits"""
    reserved = {
        name: (_memory(service, "reservations"), _limit(service))
        for name, service in _services().items()
        if _memory(service, "reservations") is not None
    }
    assert {"backend", "frontend", "nginx"} <= reserved.keys()
    for name, (reservation, limit) in reserved.items():
        assert limit is not None, f"{name} reserves memory without a limit"
        assert reservation is not None
        assert reservation < limit, f"{name}: reservation {reservation} >= {limit}"


def test_the_backend_limit_covers_the_measured_hd_export_peak() -> None:
    """Scenario: The backend limit covers the measured HD export peak"""
    backend = _services()["backend"]
    limit = _limit(backend)
    assert limit is not None
    assert limit >= MEASURED_HD_RUN_PEAK_MIB * HEADROOM
    assert _memory(backend, "reservations") is not None
