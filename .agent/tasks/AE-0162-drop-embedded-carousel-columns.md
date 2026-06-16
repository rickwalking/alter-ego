# AE-0162 — Backend: drop embedded carousel blog/distribution columns (DESTRUCTIVE, drain-gated, consent-gated)

Status: Intake
Tier: T2
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

Confirm blog_posts is the single writer (no remaining embedded-column writers); satisfy the checkpoint-drain rule (every live LangGraph checkpoint finished on pre-migration code or restarted with documented consent); author a reversible-by-backup destructive Alembic migration dropping the embedded columns; fresh-DB upgrade + drift check + downgrade verified. Consent-gated + drain-gated.

## Non-Goals

- Not executed without explicit owner consent + satisfied checkpoint-drain.
- No drop while a live checkpoint references the old shape.

## Modularization Alignment (2026-06-16)

Phase 8 of the modularization plan (§Phase 8 "Remove legacy layers and adapters") — the final phase, after
Phases 0-7 merged (PRs #15-#21). Removes the temporary migration scaffolding to zero. Class A (safe cleanup) is
behavior-preserving and holds the existing green gates with down-only ratchets; Class B (auto-publish cutover +
destructive column drop) is consent-gated + drain-gated (ADR-0008). See `docs/plans/phase-8-legacy-removal.md`.

## Acceptance Criteria

- [ ] A destructive migration SHALL drop the embedded columns, GATED by checkpoint-drain + confirmation blog_posts is the single writer
- [ ] The migration SHALL be reversible-by-backup; fresh-DB upgrade + empty-autogenerate-drift + downgrade verified
- [ ] Explicit owner consent + checkpoint-drain SHALL be satisfied first; gates.sh + check-integrity green

## Gherkin Scenarios

Not applicable — legacy-removal cleanup; verified by the green-gate safety net (and, for the Class-B behavior
change, by the updated AE-0125 safety net asserting the new approval≠release flow).

## Dependencies

- Blocks: —
- Blocked by: AE-0161
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
