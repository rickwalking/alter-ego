# AE-0336 — make review-gate slide edits actually reach the exported PDF

Status: Ready
Tier: T2
Priority: Critical
Type: Bug
Area: Backend
Owner: Unassigned
Agent Lane: architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-09-15
Updated: 2026-09-15

## Goal

An edit accepted at the review gate must appear in the exported artifact. One
write path, one read authority — no silent divergence between the LangGraph
checkpoint and the `carousel_slides` DB projection.

## Problem

Review-gate edits are written to the **LangGraph checkpoint only**. The export
renders from the **`carousel_slides` DB projection**. The two are never
reconciled, so **the reviewer's edits never reach the PDF** — the export silently
renders the pre-edit copy and reports success.

Confirmed live on carousel `dcaa5fef…` (2026-09-15). The only working path found
was to bypass the gate entirely:

```
PATCH /carousels/{id}/slides      # same LocalizedSlideReview shape; requires status=completed
POST  /carousels/{id}/republish   # synchronous, no body, mints a new artifact_version
```

That is an operator workaround, not a product. A reviewer using the UI edits,
approves, downloads the PDF, and gets their edits back missing with no error.

This is AE-0293 ("checkpoint vs DB projection read authority") made concrete —
that ADR ticket is the architectural decision this fix must land under.

## Scope

- Decide and document the read authority (AE-0293 ADR): either the projection is
  derived from the checkpoint on every gate write, or the checkpoint defers to the
  projection. Pick one; do not leave both authoritative.
- Make the review-gate approval write through to `carousel_slides` in the same
  unit of work as the checkpoint update (or make the export read the checkpoint).
- Fail closed: if the export's source and the gate's source disagree, the export
  must **fail loudly** rather than render stale copy.
- Cover the same divergence for any other gate that accepts edits.

## Non-Goals

- Changing the `LocalizedSlideReview` payload shape (the PATCH endpoint already
  uses it and works).
- Re-exporting historical carousels.
- The sanitizer's markup destruction (AE-0338) — a separate defect on the same path.

## Acceptance Criteria

- [ ] An edit approved at the review gate appears in the regenerated PDF without
      any manual `PATCH` + `republish`.
- [ ] An ADR under AE-0293 records the chosen read authority and is referenced
      from the code.
- [ ] The gate write and the projection write are atomic — a failure leaves
      neither applied.
- [ ] If checkpoint and projection diverge, the export fails with an explicit
      error naming both values; a test proves it fails.
- [ ] End-to-end test: edit at the review gate → approve → export → assert the
      edited string is present in the rendered artifact.

## Gherkin Scenarios

```gherkin
Feature: Review-gate edits reach the export

  Scenario: An edit made at the review gate is published
    Given a completed carousel at the review gate
    When the reviewer edits slide 3's heading and approves
    And the artifact is exported
    Then the exported PDF contains the edited heading

  Scenario: Divergence fails loudly
    Given the checkpoint and the slide projection hold different text for slide 3
    When the export runs
    Then the export fails with an error naming both values
    And no artifact version is minted

  Scenario: The manual path stays available
    Given a completed carousel
    When PATCH /carousels/{id}/slides is called with a LocalizedSlideReview payload
    And POST /carousels/{id}/republish is called
    Then a new artifact version is minted containing the patched text
```

## Affected Areas

- Backend: carousel export, review-gate handlers, `carousel_slides` repository
- Frontend: review gate — surface the failure if the export refuses
- Database: `carousel_slides` write path
- API: possibly the gate approval endpoint
- Tests: end-to-end edit → approve → export
- Docs: ADR (AE-0293), carousel workflow guide
- Prompts/LLM: no
- Observability: log divergence
- Deployment: no

## Dependencies

- Blocks: any reviewer trusting the review gate
- Blocked by: AE-0293 (the ADR decision) — may be folded into this ticket
- Related: AE-0335, AE-0338, AE-0339

## Implementation Plan

1. Write the failing end-to-end test (edit → approve → export → assert).
2. Settle the read authority under AE-0293; write the ADR.
3. Implement the write-through (or read-switch) atomically.
4. Add the fail-closed divergence check plus its own test.
5. Confirm the PATCH + republish path still works (regression).

## QA Checklist

- [ ] Security reviewed (who may PATCH slides)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (partial edit, concurrent edit, lock_version conflict)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-09-15

Ticket created from the AE-0330 session handoff (defect #9). Reproduced live on
carousel dcaa5fef; the PATCH + republish workaround is the only path that reached
the PDF.

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
