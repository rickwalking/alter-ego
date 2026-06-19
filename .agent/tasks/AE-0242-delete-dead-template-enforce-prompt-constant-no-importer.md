# AE-0242 — Delete dead TEMPLATE_ENFORCE prompt constant (no importer)

Status: Dev Complete
Tier: T1
Priority: Medium
Type: Refactor
Area: backend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Remove the dead `TEMPLATE_ENFORCE` persona-rewrite system prompt constant from
`agents/constants.py` so the prompt surface has exactly one fewer hardcoded
violation and no orphaned 41-line prompt masquerades as live config.

## Problem

`TEMPLATE_ENFORCE` (`backend/src/rag_backend/agents/constants.py:39`) is a 41-line
hardcoded persona-rewrite system prompt with full `{placeholders}`. The skeptical
pass re-verified it has **no importer**:
`grep -rn TEMPLATE_ENFORCE src/` → **0 importers** (only the definition site). It is
dead code — the live persona-enforce path is `persona_agent.py:88`
(`_build_style_guide`), not this constant. Because it looks like a real prompt, it
(a) inflates the "hardcoded prompt" count, (b) risks a future author migrating it to
the registry by mistake, and (c) violates the CLAUDE.md "no magic strings / prompts
live in `.md`/`.yaml`" rule with zero runtime value.

Evidence: `agents/constants.py:39`; arch-plan §1.1 table row #1 and §1.2 "Corrected
(Revision 2)"; skeptical-corrections.md row 3 ("4 active remediations + delete the
dead one").

## Scope

- `backend/src/rag_backend/agents/constants.py` — delete `TEMPLATE_ENFORCE` (and any
  now-unused helper constants/imports it alone referenced).
- Any test that asserts on `TEMPLATE_ENFORCE` directly (expected: none — confirm).

## Non-Goals

- Do **not** migrate `TEMPLATE_ENFORCE` into the registry — it is dead, not a prompt
  in use. The live persona-enforce prompt is migrated separately in AE-0243 (RES-5),
  sourced from `_build_style_guide`, **not** from this constant.
- Do not touch the legit fallback constants (`_FALLBACK_SYSTEM_PROMPT`,
  `_ALTER_EGO_FALLBACK_PROMPT`, `_JSON_REPAIR_PROMPT`).
- No change to `quality_agent.py` / `linkedin_post_generator.py` / `persona_agent.py`
  (that is AE-0243).

## Acceptance Criteria

- [x] `TEMPLATE_ENFORCE` is removed from `agents/constants.py`; the file still passes
      `ruff check` and `mypy` (no dangling import/reference).
- [x] `grep -rn "TEMPLATE_ENFORCE" backend/src backend/tests` returns **zero** hits
      after the change (proves the symbol is fully gone, not just unreferenced).
- [x] `mypy` green (agents pkg: Success, 19 files); `ruff check` green; pytest green (full
      backend gate run at the end of the prompt phase).
- [x] No behavior change anywhere — the symbol had no importer, so no call path moves.

## Gherkin Scenarios

> Pure refactor (dead-code deletion) with no public/observable behavior change — no
> `.feature` required (CLAUDE.md AE-0153). The "grep is zero" check below is the
> objective acceptance proof.

```gherkin
Feature: Dead persona-enforce prompt constant is gone

  Scenario: The constant no longer exists in the source tree
    Given the TEMPLATE_ENFORCE constant had no importer
    When it is deleted from agents/constants.py
    Then a repository grep for TEMPLATE_ENFORCE returns no matches
    And mypy, ruff, and the test suite remain green
```

## Delta

### ADDED
- None.

### MODIFIED
- `agents/constants.py` — `TEMPLATE_ENFORCE` (and any constant referenced only by it)
  deleted.

### REMOVED
- The 41-line dead `TEMPLATE_ENFORCE` prompt string.

## Affected Areas

- Backend: `agents/constants.py`.
- Frontend: none.
- Database: none.
- API: none.
- Tests: none expected (confirm no test references the symbol).
- Docs: none (the constant was never documented as live config).
- Deployment: none.

## Dependencies

- Provisional epic id: **RES-4** (Phase 1 — prompt consolidation).
- Gating ADR: **ADR-0013** is NOT a gate here; this ticket is governed by **ADR-0013…
  0017**'s parent epic but specifically realizes the prompt-registry intent of
  **ADR-0013 (prompt-registry) note** — see arch-plan §1/§10. No ADR must be Accepted
  first (dead-code deletion is unconditionally safe).
- Blocks: **AE-0243 (RES-5)** — do this first so the live `_build_style_guide` is the
  unambiguous source for the persona-enforce registry file (no confusion with the dead
  constant).
- Blocked by: none.
- Related: AE-0244 (RES-6) anti-hardcoded-prompt checker (will assert the surface is
  clean afterward).

## Implementation Plan

1. Re-confirm zero importers: `grep -rn "TEMPLATE_ENFORCE" backend/`.
2. Delete the constant (and any constant referenced **only** by it) from
   `agents/constants.py`.
3. Run `ruff`, `mypy`, `pytest`; confirm green and the grep returns nothing.

## Test Classification (CLAUDE.md AE-0153 / AE-0180)

- **Pure refactor — no public/user-visible behavior change.** The constant has no
  importer, so deleting it removes no reachable code path. **Unit tests suffice; no
  `.feature` required.**
- **No static-analysis rule added** in this ticket — the AE-0180 rule-fires mandate
  is carried by AE-0244 (RES-6), not here.
- **Affected gates:** `backend` ruff/mypy/pytest (`scripts/ci/gates.sh backend`).
- Reviewer/QA to sign off on the no-`.feature` classification.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (grep-zero confirms full removal)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-18 21:30

Created from the agent-architecture-restructure epic (RES-4). Sourced from arch-plan
Revision 2 §1.1/§1.2 and skeptical-corrections.md (dead-code re-verification).

## Files Touched

- `backend/src/rag_backend/agents/constants.py` — deleted the `# Prompt templates`
  block (the 41-line dead `TEMPLATE_ENFORCE`). The `SECTION_*`/`KEY_*` constants are
  retained (used by `_build_style_guide`), so no helper became unused.

## Test Evidence

```
$ grep -rn "TEMPLATE_ENFORCE" backend/src backend/tests   # exit 1 (zero hits)
$ cd backend/src && uv run mypy rag_backend/agents/ --explicit-package-bases
Success: no issues found in 19 source files
$ uv run ruff check src/rag_backend/agents/constants.py   # All checks passed!
```
Full backend `pytest` reproduced at the end of the prompt phase (0242–0244).

## QA Report

Pending.

## Decision Log

- **Delete, do not migrate.** The skeptical pass re-verified `TEMPLATE_ENFORCE` has no
  importer; the live persona-enforce path is `_build_style_guide`. Migrating the dead
  constant would resurrect dead code and duplicate the live prompt — so it is deleted
  outright and AE-0243 sources the registry file from the live function only.
- **Sequenced before AE-0243** so there is exactly one source of truth for the
  persona-enforce prompt when it is registry-migrated.

## Blockers

None.

## Final Summary

Pending.
