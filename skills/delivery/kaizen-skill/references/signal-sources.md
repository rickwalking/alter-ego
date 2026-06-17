# Signal Sources — Phase 0 collection & clustering

The collector subagent gathers from every source below, then **clusters into
failure classes** (recurring patterns), not a flat list of incidents. Rank
classes by `frequency × severity` and record example `file:line` refs for each.

## 0. Measurement rigor (read first — false signal poisons every downstream ticket)

Two mistakes shipped false facts in real kaizen tickets (2026-06-17); both were
only caught by the Phase-3.6 external skeptical. Do NOT repeat them:

- **Word-boundary / AST patterns, never bare substrings.** `grep 'fetch('`
  matches `refetch(` -> a false count. Use `grep -E '\bfetch\('` (or AST). The
  same applies to `isLoading`, `loading`, etc. — they are overloaded.
- **Verify "gate today / enforced" claims against the actual gate script** — never
  assume. Read `scripts/ci/gates.sh`, `scripts/ci/eslint-changed.mjs`,
  `backend/pyproject.toml`. Example trap: `lint:changed` runs `eslint --quiet`, so
  warn-level rules have **zero** CI enforcement despite "showing" in a full lint.
- **Triage tool output — detectors have false positives.** depcheck flags
  config-only devDeps (tailwindcss, eslint plugins, commitlint) as "unused";
  confirm before proposing removal.
- Every failure-class row must cite a reproducible command + real `file:line`.

## 1. CI failures (the gates that actually broke)

```bash
# Recent failed runs on the branch / repo
gh run list --limit 50 --json databaseId,headBranch,conclusion,name \
  | jq '.[] | select(.conclusion=="failure")'
# Drill into a run's failing jobs/steps
gh run view <run-id> --log-failed | tail -200
```
Map each failure to the `gates.sh` gate that failed (lint / type / strict-diff /
diff-cover / mutation / imports / arch-ratchet / integrity / …). A gate that
fails *repeatedly across PRs* is a top failure class — the question becomes "why
do developers keep producing this, and what upstream rule/doc prevents it?".

## 2. QA reports (`.agent/reports/*.qa.md`)

```bash
ls -t .agent/reports/*.qa.md
grep -hoE "🔴 .*|Blocker.*|WARN.*" .agent/reports/*.qa.md | sort | uniq -c | sort -rn
```
Recurring blocker/warning themes (same rule cited, same dimension failing) are
failure classes. Cross-reference the dimension (security / mutation / AC /
integrity) to target the right enforcement.

## 3. Code-reviewer comments (human + CodeRabbit)

```bash
gh pr list --state all --limit 30 --json number
gh pr view <PR#> --comments
```
Cluster by topic (e.g. "missing error handling", "magic strings", "N+1 query").
A topic raised by reviewers on many PRs is a class a lint rule / doc / template
should pre-empt. (See also the `ipm-coderabbit-loop` skill for live PR fixing —
Kaizen generalizes those fixes into rules.)

## 4. Integrity & suppression markers (sanctioned exceptions = rule candidates)

```bash
# Every active suppression / sanctioned exception in the tree
grep -rnE "# *(noqa|type: *ignore|nosec|pragma: *no *cover)|integrity-ok:" backend/src frontend/src
# Per-file-ignores and mypy ignore_errors (the standing debt)
grep -nE "per-file-ignores|ignore_errors|disable_error_code" backend/pyproject.toml
# Net-new gaming the guardian is currently catching
bash scripts/ci/check-integrity.sh all
```
Each `integrity-ok:` / long-lived `noqa` is a place the team chose to bypass a
rule. If the *same* bypass recurs, either the rule needs a refinement (too
broad) or a real fix is overdue — Kaizen decides which. **Never** propose
widening the suppression; that violates the ratchet invariant.

## 5. Debt markers

```bash
grep -rnE "TODO AE-[0-9]+|FIXME|HACK|XXX" backend/src frontend/src
```
Cluster `TODO AE-####` by area; a hotspot file accumulating debt is an
architecture-improvement class.

## Clustering output (`.agent/reports/kaizen-<id>.signal.md`)

```markdown
# Kaizen Signal — <id>
Window: <range> | Sources: CI, QA, reviewers, integrity, debt

## Failure Classes (ranked by frequency × severity)
| # | Class | Freq | Severity | Gate that should catch it | Example refs |
|---|-------|------|----------|---------------------------|--------------|
| 1 | New `# type: ignore` in routes to pass mypy | 7 | High | integrity | api/routes/x.py:42, … |
| 2 | Mutation survivors in service layer | 5 | High | mutation | services/y.py:88, … |

## Notes
- which classes a *new* gate would have caught vs which need a doc/template/refactor
```

## Sweep vs incident scope

- **incident**: restrict every query to the one ticket/PR (its CI run, its
  `.qa.md`, its PR comments, its diff).
- **sweep**: widen to the last N days / last M PRs (default 7 days) and prefer
  classes that appear in **≥2 incidents** — single occurrences are usually
  better handled by a normal bugfix ticket, not a rule change.
