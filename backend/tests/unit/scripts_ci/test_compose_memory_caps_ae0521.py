"""Memory caps of the production containers.

Feature: backend/tests/features/compose_memory_caps_ae0521.feature
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from defusedxml import ElementTree

REPO_ROOT = Path(__file__).resolve().parents[4]
COMPOSE = REPO_ROOT / "docker-compose.prod.yml"
CLICKHOUSE_CONFIG = REPO_ROOT / "clickhouse-config" / "low-memory.xml"
ONE_SHOT = "no"
MEMORY_VALUE = re.compile(r"^(?P<amount>\d+)(?P<unit>[kKmMgG])$")
UNIT_MIB = {"k": 1 / 1024, "m": 1, "g": 1024}
MEASURED_HD_RUN_PEAK_MIB = 1011
HEADROOM = 1.3
LANGFUSE_LIMIT_MIB = 1280
LANGFUSE_MIN_HEAP_MIB = 1024
CLICKHOUSE_LIMIT_MIB = 640
CLICKHOUSE_MAX_RATIO = 0.75
NODE_HEAP_FLAG = re.compile(r"--max-old-space-size=(?P<mib>\d+)")
NODE_NATIVE_OVERHEAD_MIB = 256

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


def test_langfuse_web_keeps_its_node_heap_below_its_container_limit() -> None:
    """Scenario: Langfuse web keeps its Node heap below its container limit"""
    langfuse = _services()["langfuse"]
    assert _limit(langfuse) == LANGFUSE_LIMIT_MIB
    environment = langfuse["environment"]
    assert isinstance(environment, dict)
    heap = NODE_HEAP_FLAG.search(str(environment.get("NODE_OPTIONS", "")))
    assert heap, "langfuse has no --max-old-space-size"
    heap_mib = int(heap.group("mib"))
    assert heap_mib >= LANGFUSE_MIN_HEAP_MIB
    assert heap_mib + NODE_NATIVE_OVERHEAD_MIB <= LANGFUSE_LIMIT_MIB


def test_clickhouse_caps_its_server_memory_below_its_container_limit() -> None:
    """Scenario: ClickHouse caps its server memory below its container limit"""
    assert _limit(_services()["clickhouse"]) == CLICKHOUSE_LIMIT_MIB
    ratio = (
        ElementTree
        .parse(CLICKHOUSE_CONFIG)
        .getroot()
        .findtext("max_server_memory_usage_to_ram_ratio")
    )
    assert ratio is not None
    assert float(ratio) <= CLICKHOUSE_MAX_RATIO
