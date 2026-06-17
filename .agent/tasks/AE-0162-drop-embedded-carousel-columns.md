# AE-0162 — Backend: drop embedded carousel blog/distribution columns (DESTRUCTIVE, drain-gated, consent-gated)

Status: Intake
Tier: T2
Class: B
Priority: High
Type: Task
Area: Backend/DB
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: feat/ae-0162-drop-embedded-carousel-columns
Kanban Card: TBD
Created: 2026-06-16
Updated: 2026-06-16

## Goal

Execute the deferred DESTRUCTIVE migration dropping blog_markdown/blog_translations/caption*/linkedin_post_* from carousel_projects, once blog_posts is the confirmed single writer and the checkpoint-drain gate is satisfied. Supersedes the drop half of AE-0133.

## Problem

AE-0127 added BlogPost.origin + an additive backfill but deliberately did NOT drop the embedded carousel columns (a destructive, drain-gated change). With the read-model projections (AE-0131) reading blog_posts, the embedded columns can be dropped once confirmed unused-as-writer.

## Scope

PRECONDITION (AE-0163 must be DONE): the embedded-column read fallback is removed and blog_posts is the single writer — this ticket only DROPS the columns once nothing reads/writes them. Then: verify no live carousel_workflow LangGraph checkpoint state carries blog_markdown/caption/linkedin_post_* keys (a resumed checkpoint would re-write dropped columns); satisfy the checkpoint-drain rule; verify the prod carousel_projects shape matches the migration's expected pre-state (prod is create_all-bootstrapped, no Alembic — see memory prod-db-schema-drift); author a reversible-by-backup destructive Alembic migration dropping the embedded columns; fresh-DB upgrade + drift check + downgrade verified. Consent-gated + drain-gated.

## Non-Goals

- Not executed without explicit owner consent + satisfied checkpoint-drain + AE-0163 done.
- No drop while a live checkpoint references the old shape, or while any code still reads/writes the embedded columns.
- Not before the merged Phases 0-7 have been observed in production (roadmap: "after production observation").

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [ ] AE-0163 SHALL be DONE first: no code reads the embedded columns (fallback removed) and no code writes them (blog_posts is the single writer)
- [ ] No live carousel_workflow checkpoint state SHALL carry blog_markdown/caption/linkedin_post_* keys (verified) — a resumed checkpoint must not re-write dropped columns
- [ ] A destructive migration SHALL drop the embedded columns, reversible-by-backup; fresh-DB upgrade + empty-autogenerate-drift + downgrade verified; prod pre-state shape verified before drop
- [ ] Explicit owner consent + checkpoint-drain SHALL be satisfied first, after production observation of Phases 0-7; gates.sh + check-integrity green

## Gherkin Scenarios

Not applicable — destructive migration; verified by the AE-0163 byte-identical reads (post-fallback-removal) + fresh-DB upgrade/downgrade/drift tests + the checkpoint-drain gate.

## Dependencies

- Blocks: —
- Blocked by: AE-0163 (+ consent + checkpoint-drain)
- Related: AE-0152

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-16

Ticket created by planner (Phase 8 breakdown).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
