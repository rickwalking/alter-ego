"""Entry point: ``python -m rag_backend.scripts.boost_validate_only <request_id>``.

Loads the ORM model registry before the autopilot package, the order the app and
the worker use, then runs ``boost_validate_only_cli``. See that module for usage.
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence

ORM_REGISTRY = "rag_backend.infrastructure.database.models"
CLI_MODULE = "rag_backend.scripts.boost_validate_only_cli"

__all__ = ["main"]


def main(argv: Sequence[str] | None = None) -> int:
    """Import the registry, then the command, and run it."""
    importlib.import_module(ORM_REGISTRY)
    command = importlib.import_module(CLI_MODULE)
    code: int = command.main(argv)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
