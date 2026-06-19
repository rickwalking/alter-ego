# AE-0234 — Docs folder indexes + plans active/historical split

Status: Intake
Tier: T2
Priority: Low
Type: Quality
Area: Docs
Owner: Unassigned
Branch: TBD
Created: 2026-06-18
Updated: 2026-06-18
Source: architect plan — `.agent/reports/frontend-migrations-and-docs.arch-plan.md` (Thread B3). Parent: AE-0231.

## Goal
Make /docs navigable: per-folder indexes and a clear active-vs-historical plan split.

## Problem
11 subfolders have no INDEX; `plans/` mixes active plans with done Phase 1–6 history;
3 stray root-level .md files.

## Scope
- Add `INDEX.md` to architecture/, guides/, plans/, decisions/, deployment/, backend/, frontend/, research/.
- Reorganize `plans/` into `active/` + `historical/`; move stray root .md into the right folder.
- Update README + any moved-doc links (incl. CLAUDE.md `docs/plans/...` references).

## Non-Goals
- No content rewrites beyond index creation + moves.

## Acceptance Criteria
- [ ] Each major folder has an INDEX.md.
- [ ] plans/ split active/historical; no stray root-level .md.
- [ ] No broken links after moves (grep clean).

## Dependencies
- Parent: AE-0231. Blocked by AE-0233 (don't index files about to move/delete).

## Progress Log
### 2026-06-18
Created from the architect plan (Thread B3).

## Files Touched
Pending.
## Test Evidence
Pending.
## QA Report
Pending.
## Blockers
None.
