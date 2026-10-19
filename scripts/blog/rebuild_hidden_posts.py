#!/usr/bin/env python3
"""Entry point of the AE-0426 hidden-post rebuild (see the packaged module).

Run from the repo root (the backend project's venv) against ``DATABASE_URL``:

    uv run --project backend python scripts/blog/rebuild_hidden_posts.py --dry-run
    uv run --project backend python scripts/blog/rebuild_hidden_posts.py --apply

The real implementation ships in the backend image as
``rag_backend.scripts.rebuild_hidden_posts``; this shim only puts ``backend/src``
on ``sys.path`` and delegates, so the ticket's path still works from a checkout.
Default is ``--dry-run``; never publishes.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND_SRC = Path(__file__).resolve().parents[2] / "backend" / "src"


def main() -> int:
    """Bootstrap ``backend/src`` and delegate to the packaged CLI."""
    if str(_BACKEND_SRC) not in sys.path:
        sys.path.insert(0, str(_BACKEND_SRC))
    from rag_backend.scripts.rebuild_hidden_posts import main as run

    return run()


if __name__ == "__main__":
    sys.exit(main())
