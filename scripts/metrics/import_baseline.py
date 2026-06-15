#!/usr/bin/env python3
"""Architecture-violation baseline for the modularization plan (AE-0078).

Measurement only — changes nothing. Scans backend/src/rag_backend with
stdlib regex (same signal Import Linter would see if its wildcards were
removed) and prints a sorted, timestamp-free report so repeated runs are
byte-identical.

Categories:
  wildcard-hidden (declared forbidden, exempted in .importlinter):
    application -> infrastructure, application -> agents
  target-forbidden (allowed or uncovered today, forbidden post-move):
    agents -> application, api -> infrastructure
  service-locator: get_container( outside bootstrap/ + api/dependencies/
  repo-commit: .commit( inside infrastructure/database adapters
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "backend" / "src" / "rag_backend"

# ---------------------------------------------------------------------------
# AE-0078 committed baseline ceiling (single source of truth).
#
# Pinned to .agent/reports/import-violations-baseline.md @ commit 716dba5
# (AE-0078, in Review). The ratchet (`--check`) compares the CURRENT tree
# against these numbers field-exact: each value may only stay equal or
# DECREASE, never increase. Regenerate the baseline report with the default
# (no-arg) invocation of this script; update these constants only when the
# committed AE-0078 artifact is intentionally re-pinned.
# ---------------------------------------------------------------------------
BASELINE_ARTIFACT = ".agent/reports/import-violations-baseline.md"
BASELINE_COMMIT = "716dba5"

# Per import category: (runtime unique-module-pairs, type-checking-only pairs).
BASELINE_PAIR_CEILING: dict[str, tuple[int, int]] = {
    "application -> infrastructure": (63, 0),
    "application -> agents": (23, 0),
    "agents -> application": (20, 2),
    # Ratcheted down 98 -> 82 by AE-0099/0101/0102 (auth/admin/conversation/
    # chat-stream routes moved behind identity/conversation facades) and 82 -> 81
    # by AE-0110 (editorial workflow routes moved behind the editorial facade).
    "api -> infrastructure": (81, 0),
}
# Non-import categories Import Linter cannot express.
# Ratcheted down 26 -> 14 by Phase 3 (AE-0099/0101/0102 resolve user/conversation
# collaborators + chat-agent construction via the module facades at the DI edge,
# not get_container()).
BASELINE_GET_CONTAINER = 14
BASELINE_COMMIT_SITES = 9

IMPORT_RE = re.compile(
    r"^\s*(?:from\s+(rag_backend\.[\w.]+)\s+import\s+(.+)|import\s+(rag_backend\.[\w.]+))",
)

CATEGORIES = [
    ("application -> infrastructure", "application", "rag_backend.infrastructure", "wildcard-hidden"),
    ("application -> agents", "application", "rag_backend.agents", "wildcard-hidden"),
    ("agents -> application", "agents", "rag_backend.application", "target-forbidden (no contract today)"),
    ("api -> infrastructure", "api", "rag_backend.infrastructure", "target-forbidden (allowed by contract 4)"),
]

# Composition-root paths allowed to resolve the DI container (AE-0080):
# bootstrap/ is the relocated composition root (ADR-0009 §9); api/dependencies/
# holds the request-scoped DI providers at the HTTP edge. The old api/app.py is
# now a thin re-export shim and no longer holds composition-root wiring.
CONTAINER_ALLOWED = ("bootstrap/", "api/dependencies/")


def module_of(path: Path) -> str:
    rel = path.relative_to(ROOT.parent)
    return str(rel.with_suffix("")).replace("/", ".").removesuffix(".__init__")


TYPE_CHECKING_RE = re.compile(r"^(\s*)if\s+(typing\.)?TYPE_CHECKING\b")


def scan_category(
    src_pkg: str, target_prefix: str
) -> tuple[list[tuple[str, str]], list[tuple[str, str]], "Counter[str]"]:
    """Collect import pairs; TYPE_CHECKING-guarded ones are tagged apart.

    Import Linter also counts TYPE_CHECKING imports by default, so they
    stay in the totals for parity — but they are zero-cost at runtime,
    so ratchet planning gets them as a separate list.
    """
    pairs: list[tuple[str, str]] = []
    tc_pairs: list[tuple[str, str]] = []
    symbols: Counter[str] = Counter()
    for f in sorted((ROOT / src_pkg).rglob("*.py")):
        tc_indent: int | None = None
        for line in f.read_text().splitlines():
            stripped = line.strip()
            tc_match = TYPE_CHECKING_RE.match(line)
            if tc_match:
                tc_indent = len(tc_match.group(1))
                continue
            if tc_indent is not None and stripped:
                indent = len(line) - len(line.lstrip())
                if indent <= tc_indent:
                    tc_indent = None
            m = IMPORT_RE.match(line)
            if not m:
                continue
            target = m.group(1) or m.group(3)
            if not target or not target.startswith(target_prefix):
                continue
            bucket = tc_pairs if tc_indent is not None else pairs
            bucket.append((module_of(f), target))
            if m.group(2):
                for sym in m.group(2).split(","):
                    sym = sym.strip().split(" as ")[0].strip("() ")
                    if sym:
                        symbols[f"{target}.{sym}"] += 1
    return pairs, tc_pairs, symbols


def scan_pattern(base: Path, pattern: str, allowed: tuple[str, ...] = ()) -> list[str]:
    hits: list[str] = []
    rx = re.compile(pattern)
    for f in sorted(base.rglob("*.py")):
        rel = str(f.relative_to(ROOT))
        if any(rel.startswith(a) or a in rel for a in allowed):
            continue
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if rx.search(line):
                hits.append(f"{module_of(f)}:{i}")
    return hits


class CategoryMetrics:
    """Structured per-category result (de-duplicated import pairs)."""

    def __init__(self, runtime: list[tuple[str, str]], type_checking: list[tuple[str, str]]):
        self.runtime = runtime
        self.type_checking = type_checking


def collect_metrics() -> tuple[dict[str, CategoryMetrics], int, int]:
    """Scan the current tree once and return every ratcheted category.

    Returns the four import categories (keyed by title), the
    ``get_container()`` locator count, and the adapter ``.commit()`` count.
    """
    categories: dict[str, CategoryMetrics] = {}
    for title, src, target, _klass in CATEGORIES:
        pairs, tc_pairs, _symbols = scan_category(src, target)
        unique = sorted(set(pairs))
        tc_unique = sorted(set(tc_pairs) - set(pairs))
        categories[title] = CategoryMetrics(unique, tc_unique)
    locator = scan_pattern(ROOT, r"get_container\(", CONTAINER_ALLOWED)
    commits = scan_pattern(ROOT / "infrastructure" / "database", r"\.commit\(")
    return categories, len(locator), len(commits)


def render_report() -> str:
    """The AE-0078 baseline report (default, no-arg invocation)."""
    out = []
    appendix: list[str] = []
    out.append("# Import-violation baseline (generated by scripts/metrics/import_baseline.py)")
    for title, src, target, klass in CATEGORIES:
        pairs, tc_pairs, symbols = scan_category(src, target)
        unique = sorted(set(pairs))
        tc_unique = sorted(set(tc_pairs) - set(pairs))
        out.append(f"\n## {title}  [{klass}]")
        out.append(
            f"import-lines={len(pairs) + len(tc_pairs)} "
            f"(runtime={len(pairs)}, type-checking-only={len(tc_pairs)}) "
            f"unique-module-pairs={len(unique) + len(tc_unique)}"
        )
        out.extend(f"- {a} -> {b}" for a, b in unique)
        out.extend(f"- {a} -> {b}  [type-checking-only]" for a, b in tc_unique)
        top = symbols.most_common(20)
        if top:
            out.append("top imported symbols (de-facto public contract):")
            out.extend(f"  {n:3d}x {s}" for s, n in top)
        appendix.extend(f"{a} -> {b}" for a, b in unique)
        appendix.extend(f"{a} -> {b}  # type-checking-only" for a, b in tc_unique)

    locator = scan_pattern(ROOT, r"get_container\(", CONTAINER_ALLOWED)
    out.append(f"\n## get_container() outside bootstrap-eligible code\ncount={len(locator)}")
    out.extend(f"- {h}" for h in locator)

    commits = scan_pattern(ROOT / "infrastructure" / "database", r"\.commit\(")
    out.append(f"\n## .commit() inside infrastructure/database adapters\ncount={len(commits)}")
    out.extend(f"- {h}" for h in commits)

    out.append("\n## Machine-readable appendix (one `module -> module` pair per line)")
    out.append("```text")
    out.extend(sorted(set(appendix)))
    out.append("```")
    return "\n".join(out) + "\n"


# --- .importlinter generation --------------------------------------------

_FORBIDDEN_CONTRACTS = (
    # (contract id, human name, title key into collect_metrics, source root,
    #  forbidden targets tuple)
    (
        "application-no-infrastructure",
        "Application layer must not depend on infrastructure (grandfathered baseline only)",
        "application -> infrastructure",
        "rag_backend.application",
        ("rag_backend.infrastructure",),
    ),
    (
        "application-no-agents",
        "Application layer must not depend on agents (grandfathered baseline only)",
        "application -> agents",
        "rag_backend.application",
        ("rag_backend.agents",),
    ),
    (
        "agents-no-application",
        "Agents must not depend on application (grandfathered baseline only)",
        "agents -> application",
        "rag_backend.agents",
        ("rag_backend.application",),
    ),
    (
        "api-no-infrastructure",
        "API must not depend on infrastructure (grandfathered baseline only)",
        "api -> infrastructure",
        "rag_backend.api",
        ("rag_backend.infrastructure",),
    ),
)


EDGE_RE = re.compile(r"(rag_backend\.[\w.]+) -> (rag_backend\.[\w.]+) \(l\.\d+(?:, l\.\d+)*\)")
IMPORTLINTER_PATH = ROOT.parents[2] / "backend" / ".importlinter"


def _broken_edges_from_cli(workdir: Path) -> set[tuple[str, str]]:
    """Run the real `lint-imports` CLI and parse the broken import edges.

    This is the ground truth CI uses (cached grimp build). The CLI wraps long
    lines, so the output is flattened before extracting `A -> B (l.N)` edges.
    """
    import subprocess

    proc = subprocess.run(
        ["uv", "run", "lint-imports"],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=False,
    )
    flat = re.sub(r"\s+", " ", proc.stdout + proc.stderr)
    return set(EDGE_RE.findall(flat))


def render_importlinter(ignores: dict[str, list[tuple[str, str]]] | None = None) -> str:
    """Emit the full .importlinter (static layer contracts + generated ignores).

    The forbidden-contract ignore lists are the generated baseline exception
    list (AE-0082): every existing violation is grandfathered, any NEW pair
    breaks the contract. No wildcards. ``ignores`` maps contract id to its
    grandfathered edge list (supplied by the CLI fixpoint); when omitted the
    ignore blocks are empty (probe pass).
    """
    ignores = ignores or {}
    out: list[str] = []
    out.append(
        "# GENERATED — do not edit ignore lists by hand.\n"
        "# Regenerate: uv run python scripts/metrics/import_baseline.py --emit-importlinter \\\n"
        "#   > backend/.importlinter   (run from repo root)\n"
        "# Static layer contracts below are hand-maintained; the per-contract\n"
        "# ignore_imports blocks are the generated AE-0082 baseline exception\n"
        "# list (existing violations grandfathered; any NEW pair breaks CI).\n"
    )
    out.append("[importlinter]")
    out.append("root_package = rag_backend")
    # External packages must be in the graph so the knowledge exit-gate contract
    # (AE-0095) can forbid sqlalchemy/fastapi/pinecone in the module's
    # application/domain layers. Enabling this leaves every existing internal-only
    # contract KEPT (they target rag_backend.* modules, unaffected by the wider
    # graph) — verified by lint-imports.
    out.append("include_external_packages = true")

    # Static global layer contracts (hand-maintained, unchanged from AE-0049).
    out.append(
        "\n# Contract: Domain must not import application, infrastructure, or API\n"
        "[importlinter:contract:domain-independence]\n"
        "name = Domain layer must not depend on outer layers\n"
        "type = forbidden\n"
        "source_modules =\n"
        "    rag_backend.domain\n"
        "forbidden_modules =\n"
        "    rag_backend.application\n"
        "    rag_backend.infrastructure\n"
        "    rag_backend.api"
    )
    out.append(
        "\n# Contract: Infrastructure must not import API\n"
        "[importlinter:contract:infrastructure-independence]\n"
        "name = Infrastructure layer must not depend on API\n"
        "type = forbidden\n"
        "source_modules =\n"
        "    rag_backend.infrastructure\n"
        "forbidden_modules =\n"
        "    rag_backend.api"
    )
    out.append(
        "\n# Contract: Domain layer must be acyclic internally\n"
        "[importlinter:contract:domain-acyclic]\n"
        "name = Domain layer must have no internal import cycles\n"
        "type = layers\n"
        "containers = rag_backend.domain\n"
        "layers =\n"
        "    protocols\n"
        "    models\n"
        "    constants"
    )

    # Module public-facade contract (AE-0081 §7c stub — real modules replace
    # _template per §7a). Keeps module internals private.
    out.append(
        "\n# Contract: module internals are private (import via the facade only)\n"
        "# AE-0081 §7c stub; real modules replace _template per §7a.\n"
        "[importlinter:contract:template-public-facade]\n"
        "name = _template internals are private (import via the facade only)\n"
        "type = forbidden\n"
        "source_modules =\n"
        "    rag_backend.api\n"
        "    rag_backend.application\n"
        "    rag_backend.domain\n"
        "    rag_backend.infrastructure\n"
        "forbidden_modules =\n"
        "    rag_backend.modules._template.domain\n"
        "    rag_backend.modules._template.application\n"
        "    rag_backend.modules._template.infrastructure\n"
        "    rag_backend.modules._template.api\n"
        "    rag_backend.modules._template.bootstrap\n"
        "    rag_backend.modules._template.constants"
    )

    # Knowledge module exit-gate (AE-0095). The knowledge bounded context lives
    # under rag_backend.modules.knowledge, OUTSIDE rag_backend.application, so the
    # global application-no-infrastructure contract does not cover it. These two
    # hand-maintained module contracts lock the Phase-2 exit gate and are the
    # reusable template every later phase copies (see
    # docs/architecture/module-conventions.md §7a / §9a).
    #
    # Contract A — application/domain isolation: the module's inner layers must
    # not import frameworks (sqlalchemy/fastapi), the vendor SDK (pinecone), or
    # the global DI container. allow_indirect_imports keeps this a per-edge gate
    # (indirect chains via infrastructure are owned by their own contracts).
    out.append(
        "\n# Contract: Knowledge module application/domain exit-gate (AE-0095)\n"
        "# The knowledge inner layers must stay free of frameworks, the vendor\n"
        "# SDK, and the global container. Currently clean (AE-0089/0092/0093):\n"
        "# no ignore_imports — any NEW such import breaks CI.\n"
        "[importlinter:contract:knowledge-application-isolation]\n"
        "name = Knowledge application/domain must not import frameworks, vendors, "
        "or the global container\n"
        "type = forbidden\n"
        "allow_indirect_imports = true\n"
        "unmatched_ignore_imports_alerting = none\n"
        "source_modules =\n"
        "    rag_backend.modules.knowledge.application\n"
        "    rag_backend.modules.knowledge.domain\n"
        "forbidden_modules =\n"
        "    sqlalchemy\n"
        "    fastapi\n"
        "    pinecone\n"
        "    rag_backend.infrastructure.container"
    )

    # Contract B — public-facade: cross-module callers (agents, api, other
    # layers) may import ONLY rag_backend.modules.knowledge (the facade); never
    # its internals. Mirrors module-conventions §7a. The one legitimate legacy
    # internal edge (api/routes/documents -> domain.commands.MetadataValue) is
    # grandfathered; agents/routes otherwise go through the facade.
    out.append(
        "\n# Contract: knowledge internals are private (import via the facade only)\n"
        "# AE-0095 — mirrors module-conventions §7a; the proven Phase-2 pattern.\n"
        "[importlinter:contract:knowledge-public-facade]\n"
        "name = knowledge internals are private (import via the facade only)\n"
        "type = forbidden\n"
        "allow_indirect_imports = true\n"
        "unmatched_ignore_imports_alerting = none\n"
        "source_modules =\n"
        "    rag_backend.api\n"
        "    rag_backend.agents\n"
        "    rag_backend.application\n"
        "    rag_backend.domain\n"
        "    rag_backend.infrastructure\n"
        "forbidden_modules =\n"
        "    rag_backend.modules.knowledge.domain\n"
        "    rag_backend.modules.knowledge.application\n"
        "    rag_backend.modules.knowledge.infrastructure\n"
        "    rag_backend.modules.knowledge.api\n"
        "    rag_backend.modules.knowledge.bootstrap\n"
        "    rag_backend.modules.knowledge.constants\n"
        "ignore_imports =\n"
        "    rag_backend.api.routes.documents -> "
        "rag_backend.modules.knowledge.domain.commands"
    )

    # Phase 3 exit gate (AE-0103) — identity + conversation; Phase 4 exit gate
    # (AE-0112) — editorial. Each mirrors the proven Phase-2 knowledge pair above.
    # All are currently clean (AE-0098..0111): application/domain layers are
    # framework/vendor/container/Postgres-free and every cross-module caller goes
    # through the facade root, so no contract needs an ignore_imports block — any
    # NEW such edge breaks CI. The editorial ACL (editorial/infrastructure) is the
    # only editorial code importing the carousel ORM; the isolation contract scopes
    # to editorial.application/domain, so the ACL is intentionally not a source.
    # See docs/architecture/module-conventions.md §7a / §9a / §11.
    for module in ("identity", "conversation", "editorial"):
        # Contract A — application/domain isolation: inner layers must not import
        # frameworks (sqlalchemy/fastapi), the global DI container, or ANY
        # infrastructure (which is where the concrete Postgres repositories live)
        # — they depend only on ports, the platform UoW, and other facades.
        out.append(
            f"\n# Contract: {module.capitalize()} module application/domain "
            "exit-gate (AE-0103)\n"
            f"# The {module} inner layers must stay free of frameworks, the global\n"
            "# container, and concrete infrastructure (incl. Postgres repos).\n"
            "# Currently clean — no ignore_imports; any NEW such import breaks CI.\n"
            f"[importlinter:contract:{module}-application-isolation]\n"
            f"name = {module.capitalize()} application/domain must not import "
            "frameworks, the global container, or infrastructure\n"
            "type = forbidden\n"
            "allow_indirect_imports = true\n"
            "unmatched_ignore_imports_alerting = none\n"
            "source_modules =\n"
            f"    rag_backend.modules.{module}.application\n"
            f"    rag_backend.modules.{module}.domain\n"
            "forbidden_modules =\n"
            "    sqlalchemy\n"
            "    fastapi\n"
            "    rag_backend.infrastructure"
        )
        # Contract B — public-facade: cross-module / cross-layer callers may
        # import ONLY rag_backend.modules.<module> (the facade root); never its
        # internals. Mirrors module-conventions §7a.
        out.append(
            f"\n# Contract: {module} internals are private "
            "(import via the facade only)\n"
            "# AE-0103 — mirrors module-conventions §7a; the proven Phase-2 pattern.\n"
            f"[importlinter:contract:{module}-public-facade]\n"
            f"name = {module} internals are private (import via the facade only)\n"
            "type = forbidden\n"
            "allow_indirect_imports = true\n"
            "unmatched_ignore_imports_alerting = none\n"
            "source_modules =\n"
            "    rag_backend.api\n"
            "    rag_backend.agents\n"
            "    rag_backend.application\n"
            "    rag_backend.domain\n"
            "    rag_backend.infrastructure\n"
            "forbidden_modules =\n"
            f"    rag_backend.modules.{module}.domain\n"
            f"    rag_backend.modules.{module}.application\n"
            f"    rag_backend.modules.{module}.infrastructure\n"
            f"    rag_backend.modules.{module}.api\n"
            f"    rag_backend.modules.{module}.bootstrap\n"
            f"    rag_backend.modules.{module}.constants"
        )

    # Generated forbidden contracts (exact baseline exception lists, no wildcards).
    for cid, cname, _key, source, targets in _FORBIDDEN_CONTRACTS:
        block = [
            f"\n# Contract: {cname}",
            "# ignore_imports below = generated AE-0082 baseline exception list",
            "# (Import Linter's own direct-edge view; any NEW edge breaks CI).",
            f"[importlinter:contract:{cid}]",
            f"name = {cname}",
            "type = forbidden",
            # Only direct imports break the contract; indirect chains such as
            # api -> application -> infrastructure are owned by their own
            # direct-edge contract, so this stays a per-edge ratchet.
            "allow_indirect_imports = true",
            # Tolerate baseline ignore entries that don't resolve to a direct
            # edge in a given grimp environment (CI's fresh graph may not
            # surface every edge the generator saw). This does NOT weaken
            # enforcement: a NEW forbidden edge absent from the ignore list
            # still breaks the contract.
            "unmatched_ignore_imports_alerting = none",
            "source_modules =",
            f"    {source}",
            "forbidden_modules =",
        ]
        block += [f"    {t}" for t in targets]
        edges = sorted(ignores.get(cid, []))
        if edges:
            block.append("ignore_imports =")
            block += [f"    {a} -> {b}" for a, b in edges]
        out.append("\n".join(block))

    return "\n".join(out) + "\n"


# Map each forbidden contract id to its (source, forbidden) prefixes so the
# CLI fixpoint can attribute a reported broken edge to the right contract.
_CONTRACT_SCOPE = {
    cid: (source, targets[0]) for cid, _cn, _k, source, targets in _FORBIDDEN_CONTRACTS
}


def _attribute_edge(importer: str, imported: str) -> str | None:
    for cid, (src, forb) in _CONTRACT_SCOPE.items():
        in_src = importer == src or importer.startswith(src + ".")
        in_forb = imported == forb or imported.startswith(forb + ".")
        if in_src and in_forb:
            return cid
    return None


def emit_importlinter_via_cli() -> str:
    """Generate `.importlinter` by reconciling against the real CLI to a fixpoint.

    Writes a candidate `.importlinter`, runs `lint-imports`, folds every broken
    edge it reports into the matching contract's grandfathered ignore list, and
    repeats until the CLI reports zero broken contracts. This guarantees the
    committed file passes the exact (cached) CI invocation regardless of grimp
    cache/squash quirks. Existing violations are grandfathered; any NEW edge —
    absent from the list — still breaks the contract.
    """
    import shutil

    workdir = IMPORTLINTER_PATH.parent
    # Match CI's fresh-checkout condition: grimp's cached build can surface a
    # few package-level squashed edges that an incremental/stale cache hides,
    # so generate against a freshly built cache (the same view CI computes).
    shutil.rmtree(workdir / ".grimp_cache", ignore_errors=True)
    saved = IMPORTLINTER_PATH.read_text() if IMPORTLINTER_PATH.exists() else None
    ignores: dict[str, list[tuple[str, str]]] = {}
    try:
        text = render_importlinter(ignores)
        for _ in range(50):  # bounded fixpoint
            IMPORTLINTER_PATH.write_text(text)
            broken = _broken_edges_from_cli(workdir)
            added = False
            for importer, imported in broken:
                cid = _attribute_edge(importer, imported)
                if cid is None:
                    continue
                bucket = ignores.setdefault(cid, [])
                if (importer, imported) not in bucket:
                    bucket.append((importer, imported))
                    added = True
            if not added:
                break
            text = render_importlinter(ignores)
    finally:
        if saved is not None:
            IMPORTLINTER_PATH.write_text(saved)
    return render_importlinter(ignores)


# --- ratchet check --------------------------------------------------------


def render_check() -> tuple[str, int]:
    """Field-exact ratchet vs the committed AE-0078 baseline.

    Compares the CURRENT tree to BASELINE_* ceilings for all six categories;
    fails (exit 1) if ANY value rises above its baseline. Counts may stay
    equal or decrease.
    """
    categories, locator, commits = collect_metrics()
    lines = [
        "# Import-boundary ratchet (scripts/metrics/import_baseline.py --check)",
        f"# Baseline: {BASELINE_ARTIFACT} @ {BASELINE_COMMIT} (AE-0078)",
    ]
    failed = False

    def compare(label: str, current: int, ceiling: int) -> None:
        nonlocal failed
        status = "OK"
        if current > ceiling:
            status = "FAIL (rose above baseline)"
            failed = True
        elif current < ceiling:
            status = "OK (ratcheted down)"
        lines.append(f"{status:28s} {label}: current={current} baseline={ceiling}")

    for key, (rt_ceil, tc_ceil) in BASELINE_PAIR_CEILING.items():
        m = categories[key]
        compare(f"{key} [runtime pairs]", len(m.runtime), rt_ceil)
        compare(f"{key} [type-checking pairs]", len(m.type_checking), tc_ceil)
    compare("get_container() locator hits", locator, BASELINE_GET_CONTAINER)
    compare(".commit() adapter hits", commits, BASELINE_COMMIT_SITES)

    lines.append("")
    lines.append("RESULT: FAIL — a category rose above baseline." if failed else "RESULT: PASS")
    return "\n".join(lines) + "\n", (1 if failed else 0)


def render_summary() -> tuple[str, int]:
    """Human-readable Markdown architecture report (AE-0085).

    Renders a GitHub-flavoured Markdown table comparing all six AE-0078
    categories on the CURRENT tree to the committed baseline ceilings, with a
    per-row status (OK / ratcheted down / FAIL). It consumes the same
    ``collect_metrics()`` + ``BASELINE_*`` single source of truth as the
    ``--check`` ratchet, so the report and the gate never disagree. The exit
    code mirrors ``--check`` (1 if any category rose above baseline), making
    this mode safe to use as the enforcing step too if desired.

    Designed to be written to ``$GITHUB_STEP_SUMMARY`` and/or uploaded as a CI
    artifact so reviewers see architecture health every run, not just
    pass/fail.
    """
    categories, locator, commits = collect_metrics()
    failed = False
    rows: list[tuple[str, int, int]] = []
    for key, (rt_ceil, tc_ceil) in BASELINE_PAIR_CEILING.items():
        m = categories[key]
        rows.append((f"{key} — runtime pairs", len(m.runtime), rt_ceil))
        rows.append((f"{key} — type-checking pairs", len(m.type_checking), tc_ceil))
    rows.append(("get_container() locator sites", locator, BASELINE_GET_CONTAINER))
    rows.append((".commit() adapter sites", commits, BASELINE_COMMIT_SITES))

    out: list[str] = []
    out.append("## Architecture report — import-boundary ratchet (AE-0085)")
    out.append("")
    out.append(f"Baseline: `{BASELINE_ARTIFACT}` @ `{BASELINE_COMMIT}` (AE-0078).")
    out.append(
        "Per-category ratchet: each count may stay equal or decrease, never rise. "
        "Enforced by `scripts/metrics/import_baseline.py --check` (AE-0082)."
    )
    out.append("")
    out.append("| Category | Current | Baseline | Status |")
    out.append("| --- | ---: | ---: | --- |")
    for label, current, ceiling in rows:
        if current > ceiling:
            failed = True
            status = "FAIL — rose above baseline"
        elif current < ceiling:
            status = "OK (ratcheted down)"
        else:
            status = "OK"
        out.append(f"| {label} | {current} | {ceiling} | {status} |")
    out.append("")
    out.append(
        "**RESULT: FAIL — a category rose above baseline.**"
        if failed
        else "**RESULT: PASS — all categories at or below baseline.**"
    )
    out.append("")
    return "\n".join(out) + "\n", (1 if failed else 0)


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--check":
        report, code = render_check()
        sys.stdout.write(report)
        return code
    if arg == "--summary":
        report, code = render_summary()
        sys.stdout.write(report)
        return code
    if arg == "--emit-importlinter":
        sys.stdout.write(emit_importlinter_via_cli())
        return 0
    sys.stdout.write(render_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
