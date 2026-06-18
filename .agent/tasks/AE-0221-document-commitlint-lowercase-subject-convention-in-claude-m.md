# AE-0221 — Document commitlint lowercase-subject convention in CLAUDE.md

Status: Review
Tier: T1
Priority: Low
Type: Quality
Area: Docs
Owner: Agent
Branch: feat/dev-wave-ae0220-0227
Created: 2026-06-18
Updated: 2026-06-18
Source: kaizen session-2026-06-18b (P3, class FC2) — `.agent/reports/kaizen-session-2026-06-18b.plan.md`

## Goal

Document the commitlint subject-case rule so authors stop tripping it with
uppercase ticket IDs in commit subjects.

## Problem

`frontend/.commitlintrc.json` extends `@commitlint/config-conventional`, whose
`subject-case` rule rejects upper/start/pascal/sentence-case subjects. Uppercase
ticket IDs (`AE-0216`) in a commit subject therefore fail the `commit-msg` hook —
recurring friction across sessions (e.g. `AE-0216 → Review` was rejected). The
convention (keep the subject all-lowercase, ticket IDs included) lives only in
memory/handoff landmines, not in `CLAUDE.md` where authors look.

## Scope

- Add one line to `CLAUDE.md` → **Git & Commits** (near the existing commitlint
  reference, ~line 92): commitlint `subject-case` forbids upper/start/pascal/
  sentence case — keep the **entire** commit subject lowercase, including ticket
  IDs (e.g. `move ae-0216 ticket to review`, not `AE-0216 → Review`).

## Non-Goals

- Do not refactor unrelated code
- **Do NOT relax `subject-case`** to allow uppercase — that would loosen the gate
  (down-ratchet). This ticket only documents the existing rule.

## Acceptance Criteria

- [x] `CLAUDE.md` Git & Commits section states the lowercase-subject convention
      with a concrete ticket-id example (`move ae-0216 ticket to review`).
- [x] commitlint config is **unchanged** (no rule weakened) — `frontend/.commitlintrc.json` untouched.

## Classification (AE-0153 / AE-0180)

Docs-only change, **no application behavior change** (AE-0153: no `.feature`).
No static-analysis rule added — commitlint already enforces — so AE-0180's
rule-fires test does not apply.

## Repro Steps

1. `git commit -m "AE-0216 → Review"` → commit-msg hook fails on `subject-case`.

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

None.

## Progress Log

### 2026-06-18

Ticket created from kaizen session-2026-06-18b (P3).

### 2026-06-18 — Dev Complete

Added the lowercase-subject convention bullet to CLAUDE.md → Git & Commits, with
the ticket-id example. commitlint config left untouched.

## Files Touched

- `CLAUDE.md` — Git & Commits: added the `subject-case` lowercase convention bullet.

## Test Evidence

```
$ grep -n "all-lowercase (commitlint" CLAUDE.md
82:- **Commit subjects must be all-lowercase (commitlint `subject-case`).** ...
$ git diff --name-only -- frontend/.commitlintrc.json   # empty: config unchanged
```
Docs-only change; commitlint still enforces the rule (this commit's own subject is lowercase).

## QA Report

Pending.

## Blockers

None.

## References

- Kaizen plan: `.agent/reports/kaizen-session-2026-06-18b.plan.md` (P3)
- Config: `frontend/.commitlintrc.json` (extends `@commitlint/config-conventional`)
