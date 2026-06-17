# AE-0179 — ESLint flat-config: guard against same-key rule override across overlapping blocks

Status: Dev Complete
Tier: T2
Priority: Medium
Type: Quality
Area: Frontend/CI
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-17
Updated: 2026-06-17

## Goal

Make it impossible for an ESLint flat-config rule defined in one config object to
be silently neutered by a later object that re-declares the same rule key for an
overlapping `files` glob.

## Problem

Kaizen learning K1 from the Phase 8 Class B QA wave. In flat config, when two
config objects both set the same rule key (e.g. `no-restricted-syntax`) and both
match a file, the later object's value **replaces** the earlier — arrays are NOT
merged. During AE-0166 a scoped `no-restricted-syntax` *warn* block for
`src/modules`/`src/components` silently overrode the global `fetch`-in-`useEffect`
**error**, so the flagship rule was unenforced in exactly the app's main
directories. It shipped green and was only caught by an adversarial QA reviewer.
See `.agent/reports/phase-8-class-b.qa-wave.md` (finding H1).

## Scope

- A check (script under `frontend/scripts/` or `scripts/ci/`, mirroring the
  boundary/circular checkers) that statically parses `eslint.config.mjs` and fails
  if the same rule key is declared in more than one config object whose `files`
  globs can overlap (or, more conservatively, any duplicate rule key across
  objects), unless explicitly allow-listed with a justification comment.
- Wire it into `npm run lint` (and document in `frontend/CLAUDE.md`).
- Document the replace-not-merge gotcha in `frontend/CLAUDE.md`.

## Non-Goals

- Not a general ESLint config linter; scoped to the duplicate-rule-key footgun.
- Not changing current rule severities (AE-0166 already settled those).

## Acceptance Criteria

- [x] A check (`scripts/check-eslint-rule-overrides.mjs`) detects a duplicate rule
      key across **overlapping** local flat-config objects and FAILS (exit 1) on a
      seeded violation; passes on the real config. Overlap-aware via micromatch
      probe paths (preset spreads excluded by reference).
- [x] Allow-list mechanism (`eslint-rule-override-allowlist.json`, rule→justification)
      for intentional, justified re-declares; seeded with the 7 current ones.
- [x] Wired into `npm run lint` (`lint:eslint-overrides`); documented in `frontend/CLAUDE.md`.
- [x] Tests cover: seeded duplicate → fail; real config → pass; allow-listed → pass
      (`src/scripts/eslint-rule-overrides.test.ts`, dogfoods AE-0180).

## Gherkin Scenarios

```gherkin
Feature: ...

  Scenario: ...
    Given ...
    When ...
    Then ...
```

## Delta

### ADDED

- ...

### MODIFIED

- ...

### REMOVED

- ...

## Affected Areas

- Backend:
- Frontend:
- Database:
- API:
- Tests:
- Docs:
- Prompts/LLM:
- Observability:
- Deployment:

## Dependencies

- Blocks:
- Blocked by:
- Related: AE-0166 (origin of the finding)

## Implementation Plan

1. ...

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-17 HH:mm

Ticket created.

## Files Touched

- `frontend/scripts/check-eslint-rule-overrides.mjs` (new) — overlap-aware guard.
- `frontend/eslint-rule-override-allowlist.json` (new) — seeded allow-list (7 rules).
- `frontend/package.json` — `lint:eslint-overrides` + chained into `lint`.
- `frontend/src/scripts/eslint-rule-overrides.test.ts` (new) — rule-fires tests.
- `frontend/CLAUDE.md` — replace-not-merge gotcha + guard docs.

## Test Evidence

```bash
$ npx vitest run src/scripts/eslint-rule-overrides.test.ts
Test Files 1 passed | Tests 3 passed
# real config -> PASS (7 allow-listed re-declares, 0 unlisted);
# seeded global-error + scoped-warn no-restricted-syntax (unlisted) -> FAILED exit 1;
# same seeded duplicate once allow-listed -> PASS.

$ bash scripts/ci/gates.sh frontend:lint   -> PASS (full chain incl. lint:eslint-overrides)
$ bash scripts/ci/check-integrity.sh frontend  -> 0 blockers
```

## QA Report

Pending.

## Decision Log

- Overlap-aware via a representative micromatch probe-path set rather than parsing
  globs symbolically (robust, uses the real config as source of truth).
- Preset spreads (eslint-config-next) excluded by reference identity: overriding a
  preset is the intended flat-config mechanism, not the footgun.
- Allow-list keyed by rule name (down-only intent): a NEW unlisted overlapping
  duplicate fails; the 7 current intentional re-declares are documented.

## Blockers

None.

## Final Summary

Pending.
