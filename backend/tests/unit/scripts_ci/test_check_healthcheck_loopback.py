"""Rule-fires tests for scripts/ci/check_healthcheck_loopback.py (AE-0390, AE-0180).

The checker fails CI when a compose ``healthcheck:`` block or a Dockerfile
``HEALTHCHECK`` names ``localhost``. A clean-tree pass is not enough: these
tests prove a seeded violation exits 1.

AE-0153: CI/config part of AE-0390. The healthcheck behaviour itself is in
backend/tests/features/workflow_tracing_and_heartbeat.feature.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess  # noqa: S404  # integrity-ok: AE-0390 — a CLI checker test must invoke a subprocess
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[4]
CHECKER = REPO_ROOT / "scripts" / "ci" / "check_healthcheck_loopback.py"
PYTHON = shutil.which("python3") or sys.executable

EXIT_OK = 0
EXIT_VIOLATION = 1

_COMPOSE_BAD = """services:
  frontend:
    image: web
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost:3000/ || exit 1"]
      interval: 30s
    environment:
      NEXTAUTH_URL: http://localhost:3001
"""
_COMPOSE_GOOD = _COMPOSE_BAD.replace("http://localhost:3000/", "http://127.0.0.1:3000/")
_DOCKERFILE_BAD = """FROM node:22-alpine
ENV API=http://localhost:8000
HEALTHCHECK --interval=30s \\
    CMD wget --spider http://localhost:3000/robots.txt || exit 1
CMD ["node", "server.js"]
"""
_DOCKERFILE_GOOD = _DOCKERFILE_BAD.replace(
    "http://localhost:3000/", "http://127.0.0.1:3000/"
)


def _load_checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("healthcheck_loopback", CHECKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("checker module spec missing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CHECKER_MOD = _load_checker()


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  # integrity-ok: AE-0390 — fixed interpreter, test-controlled paths
        [PYTHON, str(CHECKER), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def _write(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def test_repository_files_pass() -> None:
    """The committed compose files and Dockerfiles satisfy the gate."""
    result = _run()

    assert result.returncode == EXIT_OK, result.stderr
    assert "healthcheck loopback OK" in result.stdout


def test_default_scan_covers_compose_and_both_dockerfiles() -> None:
    """The default file set includes prod compose and the two service images."""
    names = {
        str(path.relative_to(REPO_ROOT)) for path in CHECKER_MOD.default_files(REPO_ROOT)
    }

    assert "docker-compose.prod.yml" in names
    assert "frontend/Dockerfile" in names
    assert "backend/Dockerfile" in names


def test_fires_on_compose_healthcheck_localhost(tmp_path: Path) -> None:
    """WHEN a compose healthcheck probes localhost THE gate SHALL fail on that line."""
    compose = _write(tmp_path, "docker-compose.seed.yml", _COMPOSE_BAD)

    result = _run(str(compose))

    assert result.returncode == EXIT_VIOLATION, result.stdout
    assert f"{compose}:5: healthcheck targets localhost" in result.stderr
    assert ":8:" not in result.stderr


def test_fires_on_dockerfile_healthcheck_continuation(tmp_path: Path) -> None:
    """WHEN a Dockerfile HEALTHCHECK continuation probes localhost THE gate SHALL fail."""
    dockerfile = _write(tmp_path, "Dockerfile", _DOCKERFILE_BAD)

    result = _run(str(dockerfile))

    assert result.returncode == EXIT_VIOLATION, result.stdout
    assert f"{dockerfile}:4: healthcheck targets localhost" in result.stderr
    assert ":2:" not in result.stderr


def test_loopback_ip_passes(tmp_path: Path) -> None:
    """127.0.0.1 probes pass; localhost outside a healthcheck is not flagged."""
    compose = _write(tmp_path, "docker-compose.seed.yml", _COMPOSE_GOOD)
    dockerfile = _write(tmp_path, "Dockerfile", _DOCKERFILE_GOOD)

    result = _run(str(compose), str(dockerfile))

    assert result.returncode == EXIT_OK, result.stderr


def test_commented_localhost_is_ignored(tmp_path: Path) -> None:
    """A comment that mentions localhost inside the block is not a probe."""
    body = _COMPOSE_GOOD.replace(
        "      interval: 30s\n", "      # not localhost: busybox resolves [::1]\n"
    )
    compose = _write(tmp_path, "docker-compose.seed.yml", body)

    result = _run(str(compose))

    assert result.returncode == EXIT_OK, result.stderr


def test_unreadable_file_fails(tmp_path: Path) -> None:
    """A missing file is a violation, not a silent pass."""
    result = _run(str(tmp_path / "missing.yml"))

    assert result.returncode == EXIT_VIOLATION
    assert "unreadable" in result.stderr
