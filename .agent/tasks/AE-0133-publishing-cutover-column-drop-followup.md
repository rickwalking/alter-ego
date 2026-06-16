# AE-0133 — Follow-up: auto-publish cutover + embedded carousel-column drop (post-Phase-6)

Status: Intake
Tier: T2
Priority: Medium
Type: Task
Area: Backend/DB
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-06-15
Updated: 2026-06-15

## Goal

Execute the two DEFERRED, behavior-changing / destructive items from Phase 6's full roadmap exit gate, once their preconditions hold: (1) the auto-publish CUTOVER — make editorial approval and public release two distinct user actions (approval never auto-publishes), which needs the Phase-7 frontend; (2) the DESTRUCTIVE drop of the embedded carousel blog/distribution columns (blog_markdown/blog_translations/caption*/linkedin_post_*) once blog_posts is the confirmed single writer and the migration window has elapsed.

## Problem

Phase 6 (AE-0123..0132) extracted publishing/blog/distribution behavior-preservingly + additively: the approval≠release CONTRACT is split (AE-0111) and the BlogPost.origin backfill is additive (AE-0127), but the actual auto-publish behavior change and the destructive column drop were deliberately deferred to avoid a behavior change + a drain-gated destructive migration inside a behind-facade phase. This ticket tracks executing them later, consent-gated.

## Scope

- Auto-publish cutover: route approval and public release as separate user actions (publishing release command becomes opt-in, not auto-triggered by approval); update the carousel publish flow + the Phase-7 frontend. THIS IS A BEHAVIOR CHANGE — the safety net must be updated to assert the NEW behavior, and the change requires explicit owner consent.
- Embedded-column drop: a destructive Alembic migration dropping blog_markdown/blog_translations/caption*/linkedin_post_* from carousel_projects, GATED by the checkpoint-drain rule (every live LangGraph checkpoint finished on pre-migration code or restarted with documented consent) and by blog_posts being the confirmed single writer (no remaining embedded-column writers).

## Non-Goals

- Not executed in Phase 6 (this is the explicit deferral).
- No drop until the migration window has elapsed + checkpoint-drain satisfied + owner consent.

## Modularization Alignment (2026-06-15)

Post-Phase-6 follow-up of the modularization plan. Behavior CHANGE (auto-publish) + DESTRUCTIVE migration (column drop) — both consent-gated and drain-gated; not behavior-preserving (the safety net is updated to the new behavior for the cutover). Preconditions: Phase 6 (publishing module + additive backfill + outbox) merged; Phase 7 frontend for the cutover; checkpoint-drain satisfied for the drop.

## Acceptance Criteria

- [ ] THE auto-publish cutover SHALL make approval and public release distinct actions (approval never auto-publishes), with the safety net updated to assert the new behavior and explicit owner consent recorded
- [ ] THE embedded-column drop SHALL be a reversible-by-backup destructive migration GATED by checkpoint-drain + confirmation that blog_posts is the single writer (no remaining embedded-column writers)
- [ ] WHEN executed THE checkpoint-drain rule SHALL be satisfied first (no schema-modifying drop while a live checkpoint references the old shape)
- [ ] gates.sh + check-integrity green; the publishing contracts remain KEPT
- [ ] THE work SHALL NOT begin without explicit owner consent (this is a behavior/destructive change)

## Gherkin Scenarios

Deferred — defined when this ticket is scheduled (the cutover changes behavior; scenarios assert the NEW approval≠release flow).

## Delta

### ADDED

- auto-publish cutover (separate release action); destructive column-drop migration (gated)

### MODIFIED

- carousel publish flow + Phase-7 frontend; the AE-0125 safety net (updated to the new behavior for the cutover)

### REMOVED

- embedded carousel blog/distribution columns (after the migration window + drain)

## Affected Areas

- Backend: publishing release flow
- Frontend: approval vs publish actions (Phase 7)
- Database: destructive column drop (gated)
- API: carousel publish flow
- Tests: safety net updated to new behavior
- Docs: cutover + drop runbook
- Prompts/LLM: none
- Observability: none
- Deployment: migration window + drain

## Dependencies

- Blocks: (none — terminal follow-up)
- Blocked by: AE-0123 (Phase 6 epic), Phase 7 frontend (for the cutover)
- Related: AE-0111, AE-0127, AE-0132, ADR-0009

## Implementation Plan

1. (Consent + Phase 7) Auto-publish cutover with updated safety net.
2. (Drain + window) Destructive embedded-column drop migration.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-15

Ticket created during Phase 6 planning to track the explicitly-deferred auto-publish cutover + embedded-column drop (architect validate-round-1 finding P6-R1-004).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

Deferred by design — requires owner consent (behavior/destructive change) + Phase 7 frontend + checkpoint-drain.

## Final Summary

Pending.
