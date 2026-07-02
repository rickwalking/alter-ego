"""Rule-fires tests for scripts/check_redis_factory.py (AE-0302, AE-0180).

The checker enforces that every backend Redis client is built by the
sanctioned authenticated factory. Per AE-0180, the test proves the rule FIRES
on a seeded violation — a clean-tree pass proves nothing.

    Gherkin: tests/features/redis_auth.feature —
      "a direct Redis construction outside the factory is caught"
"""

from __future__ import annotations

import shutil
import subprocess  # noqa: S404  # integrity-ok: AE-0302 — a test for a CLI checker must invoke a subprocess (mirrors test_gate_capture.py / test_check_env_permissions.py)
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
CHECKER = REPO_ROOT / "scripts" / "check_redis_factory.py"
PYTHON = shutil.which("python3") or sys.executable

EXIT_VIOLATION = 1
FACTORY_RELATIVE = "infrastructure/redis_clients/factory.py"

_SEEDED_DIRECT_IMPORT = "from redis.asyncio import Redis\n"
_SEEDED_PLAIN_IMPORT = "import redis\n"
_CLEAN_FIRST_PARTY = (
    "from rag_backend.infrastructure.redis_clients import create_redis_client\n"
)


def _run(*dirs: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603  # integrity-ok: AE-0302 — fixed interpreter, test-controlled temp dirs
        [PYTHON, str(CHECKER), *map(str, dirs)],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def test_fires_on_seeded_redis_import(tmp_path: Path) -> None:
    violating = tmp_path / "sneaky_consumer.py"
    violating.write_text(_SEEDED_DIRECT_IMPORT, encoding="utf-8")

    result = _run(tmp_path)

    assert result.returncode == EXIT_VIOLATION, result.stdout + result.stderr
    assert "sneaky_consumer.py" in result.stderr


def test_fires_on_seeded_plain_import(tmp_path: Path) -> None:
    (tmp_path / "cache.py").write_text(_SEEDED_PLAIN_IMPORT, encoding="utf-8")

    result = _run(tmp_path)

    assert result.returncode == EXIT_VIOLATION, result.stdout + result.stderr


def test_factory_module_itself_is_allowed(tmp_path: Path) -> None:
    factory = tmp_path / FACTORY_RELATIVE
    factory.parent.mkdir(parents=True)
    factory.write_text(_SEEDED_DIRECT_IMPORT, encoding="utf-8")

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr


def test_first_party_redis_clients_import_is_not_flagged(tmp_path: Path) -> None:
    (tmp_path / "consumer.py").write_text(_CLEAN_FIRST_PARTY, encoding="utf-8")

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr


def test_real_tree_is_clean() -> None:
    result = _run()

    assert result.returncode == 0, result.stdout + result.stderr
