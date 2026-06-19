# AE-0231 — Documentation reorganization and cleanup (epic)

Status: Intake
Tier: T3
Priority: Medium
Type: Quality
Area: Docs
Owner: Unassigned
Branch: TBD
Created: 2026-06-18
Updated: 2026-06-18
Source: architect plan — `.agent/reports/frontend-migrations-and-docs.arch-plan.md` (Thread B epic).

## Goal

Refactor /docs: update stale docs, delete/archive deprecated ones, and impose
consistent organization (folder indexes, active/historical split) — an area never
previously ticketed.

## Problem

Docs inventory (scan) found: ~11 superseded/stale delete-or-archive candidates, 6
guides bloated to 1.7k–2.3k lines (vs the <400 norm), no per-folder indexes, plans/
mixing active + historical, 3 stray root-level .md files, ADR-0009 stuck "Proposed",
and a stale `API_CONTRACT.md` referencing removed UI. (Correction: ADR-011/012 ARE
already in the CLAUDE.md index — the scan was wrong on that point.)

## Scope (child tickets)

- AE-0232 (B1) — quick wins: status headers + ADR-0009 → Accepted.
- AE-0233 (B2) — delete/archive superseded docs (with inbound-link checks).
- AE-0234 (B3) — folder INDEX.md files + plans active/historical split.
- AE-0235 (B4) — de-bloat the 6 oversized guides (quick-ref + deep-dive).
- AE-0236 (B5) — fix stale content (API_CONTRACT, legacy-removal status).

## Non-Goals

- No code changes; docs only.
- No hard deletion of inbound-linked docs without redirecting links (use archive/).

## Acceptance Criteria

- [ ] All 5 child tickets (AE-0232..0236) completed.
- [ ] /docs has per-folder indexes; plans split active/historical; no stray root .md.
- [ ] No broken inbound links after deletions/moves.

## Dependencies

- Recommend `/planner-skill` validate/refine the child breakdown before dev.
- Sequencing: B1+B5 (cheap, parallel) → B2 → B3 → B4.

## Progress Log

### 2026-06-18
Created from the architect plan (Thread B epic). Child specs in AE-0232..0236.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
