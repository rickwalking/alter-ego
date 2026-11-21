# AE-0639 — The drift reconciler clears a stale content gate

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0639-drift-clears-content-gate
Kanban Card: TBD
Created: 2026-11-21
Updated: 2026-11-21

## Goal

When the drift reconciler converges a checkpoint, the fail-closed content gate follows the clean report.

## Problem

Prod carousel 4223b53a, Retry at 2026-11-21 18:42: the content gate blocked slide 3 on `translation_shape_mismatch`
(EN shape `features:0` against PT `intro:plain`) at 18:59:56. At 19:00:17 the drift reconciler converged the
checkpoint: `presentation_validation` became valid with 0 violations, but `content_gate_validation` stayed
blocking. The autopilot read the stale gate, rewrote slide 3 five times for a violation the slides no longer had, and
escalated. Re-validating the stored slides gives no violation, and every voice score is at least 70.

The reconciler also detects drift only from `presentation_validation`, so a checkpoint whose only blocking report is
a stale `content_gate_validation` is never converged.

## Scope

- `carousel_drift_reconciler`: a blocking `content_gate_validation` counts as drift, and a convergence writes it as
  `{}` (as an owner edit does when nothing blocks).
- `content_fix_mode.is_fix_revision`: an owner Retry (every note starts with `OWNER_RETRY_NOTE_PREFIX` and names no
  slide) of a content gate that already passes is a fix, so it re-drafts nothing and the autopilot approves the clean
  gate. Telegram offers only "Tentar de novo" on an escalation, so this Retry must be safe. Other system notes of a
  passing gate (autopilot persona revise, named-slide notes) keep their rework.

## Non-Goals

- Do not change the gate, the validator or the autopilot slide fix.

## Acceptance Criteria

- [ ] A clean projection with a stale blocking content gate is converged and the gate is written empty.
- [ ] A convergence of a blocking presentation report also writes the content gate empty.
- [ ] An owner Retry of a passing content gate is a fix (no redraft); an autopilot persona revise or a note naming a
      slide is still a rework.

## Repro Steps

1. A clean projection with a checkpoint whose `content_gate_validation` blocks.
2. Run the drift reconciler tick.
3. Before: nothing converges (or the gate stays blocking). After: the gate is `{}`.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-11-21 19:20

Ticket created from the 18:42 Retry on carousel 4223b53a.

## Files Touched

- `backend/src/rag_backend/infrastructure/database/carousel_drift_reconciler.py`
- `backend/tests/features/drift_clears_content_gate_ae0639.feature` (new)
- `backend/tests/unit/infrastructure/test_carousel_drift_reconciler.py`
- `backend/src/rag_backend/application/services/carousel/content_fix_mode.py`
- `backend/src/rag_backend/domain/constants/content_feedback.py`
- `backend/tests/unit/application/test_content_fix_mode_ae0636.py`
- `backend/tests/features/content_fix_revision_ae0636.feature`

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
