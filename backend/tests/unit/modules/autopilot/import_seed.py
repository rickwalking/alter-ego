"""Run ``lint-imports`` against a seeded copy of the source tree (QA r2 R6).

Rule-fires tests must not write into ``src/``: a crash or a parallel run
would leave the seed behind. The package is copied into a temporary
directory, the seed is planted there, and ``PYTHONPATH`` points
``lint-imports`` at the copy. The real ``.importlinter`` is used, limited to
one contract, with the grimp cache disabled.

_LINT_IMPORTS is the absolute path to the venv console script, so there is no PATH
lookup.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # noqa: S404  # integrity-ok: rule-fires test must run the lint-imports CLI
import sys
from dataclasses import dataclass
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[4]
_PACKAGE = "rag_backend"
_CONFIG = BACKEND / ".importlinter"
_IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc")
_PYTHONPATH = "PYTHONPATH"
_LINT_IMPORTS = Path(sys.executable).with_name("lint-imports")


@dataclass(frozen=True, kw_only=True)
class ImportSeed:
    """One planted module, relative to the ``rag_backend`` package."""

    relative_path: str
    source: str
    contract_id: str


def run_seeded_lint(
    seed: ImportSeed, workdir: Path
) -> subprocess.CompletedProcess[str]:
    """Copy the package into ``workdir``, plant the seed, run one contract."""
    root = workdir / "src"
    shutil.copytree(BACKEND / "src" / _PACKAGE, root / _PACKAGE, ignore=_IGNORED)
    (root / _PACKAGE / seed.relative_path).write_text(seed.source, encoding="utf-8")
    env = {**os.environ, _PYTHONPATH: str(root)}
    return subprocess.run(  # noqa: S603  # integrity-ok: fixed venv executable, test-controlled args
        [
            str(_LINT_IMPORTS),
            "--config",
            str(_CONFIG),
            "--contract",
            seed.contract_id,
            "--no-cache",
        ],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def source_tree_has(relative_path: str) -> bool:
    """True when the real source tree contains ``relative_path``."""
    return (BACKEND / "src" / _PACKAGE / relative_path).exists()
