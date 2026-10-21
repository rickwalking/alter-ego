#!/usr/bin/env python3
"""Gherkin scenario reference ratchet (AE-0446).

CLAUDE.md: "Gherkin-first ... Tests should reference Gherkin scenarios in
comments". This gate makes that mechanical for NEW scenarios: every
``Scenario:`` / ``Scenario Outline:`` in a ``.feature`` file must be referenced
by a test (``# Scenario: <title>`` / ``// Scenario: <title>``), unless it is
listed in the grandfathered baseline (the pre-existing backlog, measured when
the gate was introduced). The baseline only ever shrinks: add a test reference,
then regenerate it with ``--update-baseline``.

A reference matches after normalisation (lowercase; every non-alphanumeric run,
including comment markers and line breaks, becomes one space), so a title
wrapped over two comment lines still counts.

Usage:
    python scripts/check_gherkin_refs.py [--scope backend|frontend|all]
    python scripts/check_gherkin_refs.py --update-baseline
Exits 1 when a scenario outside the baseline has no test reference.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BASELINE = _REPO_ROOT / "scripts" / "gherkin_refs_baseline.json"
_FEATURE_ROOTS = {
    "backend": _REPO_ROOT / "backend" / "tests" / "features",
    "frontend": _REPO_ROOT / "frontend" / "tests" / "features",
}
_TEST_ROOTS = (
    (_REPO_ROOT / "backend" / "tests", ("*.py",)),
    (_REPO_ROOT / "frontend" / "src", ("*.test.ts", "*.test.tsx")),
    (_REPO_ROOT / "frontend" / "tests", ("*.ts", "*.tsx")),
)
_SCENARIO_LINE = re.compile(r"^\s*Scenario(?: Outline)?:\s*(?P<title>.+?)\s*$")
_NON_ALNUM = re.compile(r"[^0-9a-z]+")
_SCOPE_ALL = "all"
_BASELINE_KEY = "unreferenced"


@dataclass(frozen=True)
class GherkinScenario:
    """One scenario title in a feature file (``identity`` is baseline-stable)."""

    feature: str
    title: str

    @property
    def identity(self) -> str:
        """``<feature path>::<title>``, the key stored in the baseline."""
        return f"{self.feature}::{self.title}"


def _normalise(text: str) -> str:
    return _NON_ALNUM.sub(" ", text.lower()).strip()


def collect_scenarios(feature_root: Path, repo_root: Path) -> list[GherkinScenario]:
    """Every scenario title under ``feature_root``, in file order."""
    scenarios: list[GherkinScenario] = []
    for path in sorted(feature_root.rglob("*.feature")):
        relative = path.relative_to(repo_root).as_posix()
        for line in path.read_text(encoding="utf-8").splitlines():
            match = _SCENARIO_LINE.match(line)
            if match:
                scenarios.append(GherkinScenario(relative, match.group("title")))
    return scenarios


def load_test_corpus(test_roots: tuple[tuple[Path, tuple[str, ...]], ...]) -> str:
    """All test sources, normalised and joined (one searchable string)."""
    chunks: list[str] = []
    for root, patterns in test_roots:
        if not root.exists():
            continue
        for pattern in patterns:
            for path in root.rglob(pattern):
                if "node_modules" in path.parts:
                    continue
                chunks.append(_normalise(path.read_text(encoding="utf-8")))
    return " | ".join(chunks)


def is_referenced(scenario: GherkinScenario, corpus: str) -> bool:
    """True when a test names the scenario after a ``Scenario:`` marker."""
    title = _normalise(scenario.title)
    return f"scenario {title}" in corpus or f"scenario outline {title}" in corpus


def unreferenced(scenarios: list[GherkinScenario], corpus: str) -> list[str]:
    """Sorted identities of the scenarios no test references."""
    return sorted({s.identity for s in scenarios if not is_referenced(s, corpus)})


def load_baseline(path: Path) -> set[str]:
    """The grandfathered identities (an empty set when there is no file)."""
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get(_BASELINE_KEY, []))


def update_baseline(path: Path, corpus: str) -> int:
    """Rewrite the baseline, shrink-only once it exists (never grandfather new debt)."""
    scenarios = [
        scenario
        for root in _FEATURE_ROOTS.values()
        for scenario in collect_scenarios(root, _REPO_ROOT)
    ]
    missing = set(unreferenced(scenarios, corpus))
    if path.exists():
        grown = sorted(missing - load_baseline(path))
        if grown:
            _report(grown, [])
            print("Refusing to grow the baseline: reference these scenarios instead.")
            return 1
    payload = {_BASELINE_KEY: sorted(missing)}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Baseline written: {len(missing)} unreferenced scenario(s).")
    return 0


def _feature_roots(scope: str) -> list[Path]:
    if scope == _SCOPE_ALL:
        return list(_FEATURE_ROOTS.values())
    return [_FEATURE_ROOTS[scope]]


def _report(new: list[str], resolved: list[str]) -> None:
    for identity in new:
        print(f"UNREFERENCED SCENARIO (no test names it): {identity}")
    if new:
        print(
            "Add a test with a '# Scenario: <title>' / '// Scenario: <title>' "
            "comment for each scenario above (AE-0446)."
        )
    if resolved:
        print(
            f"{len(resolved)} grandfathered scenario(s) now have a test: run "
            "`python scripts/check_gherkin_refs.py --update-baseline` to shrink "
            "the baseline."
        )


def main(argv: list[str] | None = None) -> int:
    """Run the ratchet; ``--update-baseline`` rewrites the grandfathered list."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scope", choices=[*_FEATURE_ROOTS, _SCOPE_ALL], default=_SCOPE_ALL
    )
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args(argv)

    corpus = load_test_corpus(_TEST_ROOTS)
    if args.update_baseline:
        return update_baseline(_BASELINE, corpus)
    scenarios = [
        scenario
        for root in _feature_roots(args.scope)
        for scenario in collect_scenarios(root, _REPO_ROOT)
    ]
    missing = unreferenced(scenarios, corpus)

    baseline = load_baseline(_BASELINE)
    new = [identity for identity in missing if identity not in baseline]
    scoped = {s.identity for s in scenarios}
    resolved = sorted((baseline & scoped) - set(missing))
    _report(new, resolved)
    print(
        f"gherkin refs ({args.scope}): {len(scenarios)} scenarios, "
        f"{len(missing)} unreferenced, {len(new)} new."
    )
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
