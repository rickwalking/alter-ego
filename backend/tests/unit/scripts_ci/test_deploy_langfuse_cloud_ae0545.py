"""The Langfuse stack is off the droplet and the deploy wires Langfuse Cloud.

Feature: backend/tests/features/langfuse_cloud_ae0545.feature
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
COMPOSE = REPO_ROOT / "docker-compose.prod.yml"
DEPLOY = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
CLOUD_HOST = "https://cloud.langfuse.com"
SELF_HOSTED_SERVICES = {
    "langfuse",
    "langfuse-worker",
    "langfuse-db-init",
    "clickhouse",
    "minio",
    "minio-init",
}
SELF_HOSTED_VOLUMES = {"clickhouse_data", "minio_data"}
SELF_HOSTED_SECRETS = (
    "LANGFUSE_SALT",
    "LANGFUSE_NEXTAUTH_SECRET",
    "LANGFUSE_ENCRYPTION_KEY",
    "LANGFUSE_CLICKHOUSE_PASSWORD",
    "LANGFUSE_MINIO_PASSWORD",
)
NON_BLANK_LOOP = re.compile(r"for var in (?P<names>[A-Z_ ]+); do")


def _compose() -> dict[str, dict[str, object]]:
    document = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def _deploy() -> str:
    return DEPLOY.read_text(encoding="utf-8")


def test_the_langfuse_stack_no_longer_runs_on_the_droplet() -> None:
    """Scenario: The Langfuse stack no longer runs on the droplet"""
    document = _compose()
    services = document["services"]
    assert {"backend", "postgres", "redis"} <= services.keys()
    assert not SELF_HOSTED_SERVICES & services.keys()
    assert not SELF_HOSTED_VOLUMES & document["volumes"].keys()
    backend = services["backend"]
    assert isinstance(backend, dict)
    environment = backend["environment"]
    assert isinstance(environment, dict)
    assert environment["LANGFUSE_HOST"] == f"${{LANGFUSE_HOST:-{CLOUD_HOST}}}"
    for service in services.values():
        assert isinstance(service, dict)
        depends_on = service.get("depends_on", {})
        assert not SELF_HOSTED_SERVICES & set(depends_on)


def test_the_deploy_wires_the_cloud_keys_without_requiring_them() -> None:
    """Scenario: The deploy wires the Langfuse Cloud keys without requiring them"""
    text = _deploy()
    assert "LANGFUSE_PUBLIC_KEY=${{ secrets.LANGFUSE_CLOUD_PUBLIC_KEY }}" in text
    assert "LANGFUSE_SECRET_KEY=${{ secrets.LANGFUSE_CLOUD_SECRET_KEY }}" in text
    assert (
        f"LANGFUSE_HOST=${{{{ vars.LANGFUSE_CLOUD_HOST || '{CLOUD_HOST}' }}}}" in text
    )
    for name in SELF_HOSTED_SECRETS:
        assert name not in text
    loops = NON_BLANK_LOOP.findall(text)
    assert loops, "deploy.yml lost its non-blank env check"
    required = {name for names in loops for name in names.split()}
    assert "REDIS_PASSWORD" in required
    assert not {name for name in required if name.startswith("LANGFUSE")}


def test_the_deploy_removes_the_old_langfuse_containers() -> None:
    """Scenario: The deploy removes the old Langfuse containers"""
    text = _deploy()
    assert "docker compose -f docker-compose.prod.yml down --remove-orphans\n" in text
    assert "docker compose -f docker-compose.prod.yml down\n" not in text
