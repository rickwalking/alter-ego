#!/usr/bin/env python3
"""Redis client factory enforcement checker (AE-0302).

Every backend Redis client must be built by the single sanctioned factory
(``rag_backend/infrastructure/redis_clients/factory.py``) so it carries the
production credential. This check flags any other backend source file that
imports the ``redis`` package — you cannot construct a client without the
import, so import-detection catches ``redis.Redis(...)``, ``Redis.from_url``
and ``ConnectionPool`` bypasses alike (``redis_clients``, the first-party
package, does not match the ``\\bredis\\b`` word boundary).

Usage:
    python scripts/check_redis_factory.py [DIR ...]
Exits 1 (and prints each violation) if any file outside the factory imports
redis, else 0.

Rule-fires regression test (AE-0180 standard):
    backend/tests/unit/scripts_ci/test_check_redis_factory.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DIRS = (
    _REPO_ROOT / "backend" / "src" / "rag_backend",
    # Tests too (external QA R1): a test constructing a raw client would
    # otherwise dodge the guarantee unnoticed.
    _REPO_ROOT / "backend" / "tests",
)

# The only file allowed to import the redis package (suffix-matched so seeded
# test trees can stage their own factory at the same relative location).
ALLOWED_FACTORY_SUFFIX = "infrastructure/redis_clients/factory.py"

# Static imports AND the dynamic-import escape hatches (external QA R1):
# __import__("redis"...) / import_module("redis"...).
_REDIS_IMPORT = re.compile(
    r"^\s*(?:from\s+redis(?:\.[\w.]+)?\s+import\b|import\s+redis\b)"
    r"|__import__\(\s*[\"']redis[\"'.]"
    r"|import_module\(\s*[\"']redis[\"'.]"
)

VIOLATION_MESSAGE = (
    "{path}:{line}: direct redis import outside the sanctioned factory "
    f"({ALLOWED_FACTORY_SUFFIX}) — build clients via "
    "rag_backend.infrastructure.redis_clients.create_redis_client (AE-0302)"
)


def _iter_violations(directory: Path) -> list[str]:
    violations: list[str] = []
    for path in sorted(directory.rglob("*.py")):
        if path.as_posix().endswith(ALLOWED_FACTORY_SUFFIX):
            continue
        for lineno, text in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
        ):
            if _REDIS_IMPORT.search(text):
                violations.append(
                    VIOLATION_MESSAGE.format(path=path, line=lineno)
                )
    return violations


def main(argv: list[str]) -> int:
    directories = [Path(arg) for arg in argv] if argv else list(_DEFAULT_DIRS)
    violations: list[str] = []
    for directory in directories:
        violations.extend(_iter_violations(directory))
    if violations:
        print("\n".join(violations), file=sys.stderr)
        return 1
    print(f"redis-factory check OK ({len(directories)} dir(s) scanned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
