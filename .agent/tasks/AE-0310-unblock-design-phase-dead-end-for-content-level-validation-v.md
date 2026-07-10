# AE-0310 — Unblock design-phase dead-end for content-level validation violations

Status: Ready
Tier: T2
Priority: High
Type: Bugfix
Area: cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-07-10
Updated: 2026-07-10

## Goal

A reviewer parked at the **design** step with blocking content-level
presentation violations always has a working path forward in the UI: either
edit the offending slide copy in place, or send the workflow back to the
content phase for regeneration. Neither path exists today — every design
revise is a silent no-op loop.

## Problem

Prod incident (project `38affb3e`, 2026-07-07): slide 4 carried blocking
violations (`drafting_scaffold_present`, `body_too_long`) discovered at the
design step. The reviewer hit "revise" twice, pasting the violations as
feedback. Both times nothing changed, because:

1. The design ensure (`_ensure_design_artifacts`) re-applies design tokens
   unconditionally on every revise, but **never runs presentation
   validation at all** — validation only executes on the content-approve
   path. So the stored `presentation_validation` goes stale **by
   omission** (its `validated_at` never moved past the first run), not by
   a `design_applied` skip. (Corrected by cold-critic r2: there is no
   ensure-skip guard to remove; the fix is *adding* validation to the
   design ensure/re-render path.)
2. Design revises can never fix content: the broken text lives in
   `localized_slides` (content-phase output), and the design phase only
   consumes it.
3. The slide-edit escape hatch (`structured_feedback.edited_localized_slides`)
   is rejected by the HTTP gate for any checkpoint phase except content
   (`ERR_EDITED_SLIDES_CONTENT_PHASE_ONLY`), and `_edited_slide_updates`
   short-circuits off-content — edits submitted from design are ignored.

Result: an infinite revise loop, resolved only by manual checkpoint surgery
in prod.

## Scope

- Backend: **this ticket owns the full `edited_localized_slides`
  allowlist widening to `{content, design, final_review}`** — the HTTP
  gate and `_edited_slide_updates` are a single shared surface; widening
  it piecemeal across tickets risks a half-applied allowlist (cold-critic
  r2). Rename the content-only constant/error to reflect the set. Apply
  semantics are uniform across the three phases: apply edits to
  `localized_slides`, re-run presentation validation, store the fresh
  report. AE-0314 consumes this surface for its editors.
- Backend: accept `structured_feedback.target_phase = content` on a design
  revise (send-back): reset `content_approved`, route feedback to
  `phase_feedback[content]` (keyed by target phase, not current phase — same
  fix class as AE-0288), and re-enter the content node. Preserve generated
  images via the existing outline-heading-hash preservation.
- Backend: the design ensure/re-render path runs
  `validate_localized_slides` and stores a fresh `presentation_validation`
  report on every execution (this is an **addition** — the ensure applies
  design tokens today but never validates). A plain design revise with
  neither edits nor target phase therefore re-validates; if the fresh
  report still blocks, the node re-interrupts with it (the reviewer then
  picks an explicit recovery action — edit or send-back).
- Frontend: when the design step shows blocking violations, the two
  recovery actions are **visually dominant**: "Edit slide copy" (inline
  editor for the flagged slides, submitting `edited_localized_slides`)
  and "Send back to content" (submits `target_phase: content` with
  feedback). Plain "revise" is de-emphasized while a blocking report is
  present, and the re-interrupt payload carries a client-displayable hint
  ("direct edits or send-back resolve these violations; revise alone does
  not modify content") — otherwise the fix turns the silent loop into a
  noisy one that burns the revision cap (cold-critic r3).
- Frontend: the violation panel links each violation to its slide editor.
- Cap-exhaustion escape (pinned): submitting `edited_localized_slides`
  does **not** consume any revision cap — edits are human input, not LLM
  regenerations; the cap exists to bound LLM spend and regeneration
  churn. A reviewer who exhausts both the design and content caps can
  therefore always still fix copy via direct edits (or AE-0311's
  deterministic repair, which is also uncapped), so no carousel is ever
  cap-deadlocked.

## Non-Goals

- No automatic repair (AE-0311 covers the fix-issues button).
- No changes to final_review send-back semantics beyond sharing the
  target-phase routing helper (the full AE-0290 regeneration fix stays in
  its own lane).
- No new validation rules.

## Acceptance Criteria

- [ ] Submitting edited slides from the design step updates
      `localized_slides`, re-validates, and clears the blocking report when
      the edits fix the violations.
- [ ] A design revise with `target_phase: content` re-enters the content
      phase, regenerates flagged copy with the feedback, and preserves
      slide images for unchanged outline headings.
- [ ] A plain design revise while a blocking validation report exists
      re-runs validation (`validated_at` advances) instead of no-op looping.
- [ ] Feedback from a target-phase send-back lands in
      `phase_feedback[target_phase]`, not the current phase.
- [ ] The design step UI exposes both recovery actions whenever blocking
      violations are present, and they work end-to-end against prod-shaped
      state (regression fixture derived from project 38affb3e).
- [ ] Revision cap accounting rule (pinned): a design→content send-back
      increments `revision_count[content]` (the phase whose LLM re-runs);
      a plain design revise increments `revision_count[design]`;
      submitting `edited_localized_slides` increments **no** counter
      (human edits are uncapped — the guaranteed escape hatch when caps
      are exhausted). The cap check evaluates the counter of the phase
      that would re-run, and the cap-exceeded error names that phase
      (consumed by AE-0315's typed 409 copy). **Known pre-existing
      divergence being fixed** (cold-critic r4 verified): today the cap
      CHECK reads `revision_count[current_phase]` while the send-back
      INCREMENT bumps `revision_count[target_phase]` — they already
      disagree on the existing final_review→content path. The fix makes
      the check target-aware for ALL send-back sources, so a regression
      test pins the existing final_review→content cap semantics alongside
      the new design→content path. Covered by Gherkin scenarios
      exhausting the content cap via send-backs (from both design and
      final_review) and editing past an exhausted cap. **In-flight
      transition accepted and documented** (cold-critic r5): a rare
      project that accumulated ≥cap content send-backs under the old
      divergent accounting is newly rejected — acceptable because the
      uncapped edit escape hatch always remains. The cap-exceeded client
      copy ALWAYS points to the uncapped edit path ("you can still edit
      the text directly") so the escape is discoverable, not tribal
      knowledge (cold-critic r6), and a pre-deploy query enumerates the
      affected in-flight cohort for the release notes.
- [ ] A plain design revise while a blocking report is present does NOT
      consume the design revision cap (it is provably a content no-op —
      re-validate and re-interrupt only), and the UI disables the plain
      revise action in that state, leaving edit/send-back as the
      actionable paths (cold-critic r5: otherwise five confused clicks
      exhaust the cap).

## Gherkin Scenarios

```gherkin
Feature: Design-step recovery from content-level violations

  Scenario: Reviewer edits the flagged slide in place at design
    Given a workflow parked at design with a blocking violation on slide 4
    When the reviewer submits corrected copy for slide 4 from the design step
    Then localized_slides is updated with the edited copy
    And presentation validation re-runs and reports valid
    And the design step re-renders and awaits approval without violations

  Scenario: Reviewer sends the workflow back to content from design
    Given a workflow parked at design with a blocking violation on slide 4
    When the reviewer submits a revise with target phase content and feedback
    Then the workflow re-enters the content phase with that feedback
    And slide images for unchanged outline headings are preserved

  Scenario: Plain design revise re-validates instead of looping
    Given a stored blocking validation report at the design step
    When the reviewer submits a revise without edits or target phase
    Then the design artifact re-renders and validation re-runs
    And validated_at advances past the stored report

  Scenario Outline: Send-backs consume the target phase's revision budget
    Given the content phase has one revision remaining before its cap
    When the reviewer sends the workflow back to content from <source> twice
    Then the first send-back re-enters content and increments its counter
    And the second is rejected with a cap error naming the content phase

    Examples:
      | source       |
      | design       |
      | final_review |

  Scenario: Direct edits remain available after all caps are exhausted
    Given both the design and content revision caps are exhausted
    And a blocking violation is present at the design step
    When the reviewer submits corrected copy via the inline editor
    Then the edit is applied and re-validated without a cap error
    And the workflow can proceed once validation passes
```

## Delta

### ADDED

- Design-phase acceptance of `edited_localized_slides` and
  `target_phase: content`.
- Design-step recovery UI (inline slide editor + send-back action).

### MODIFIED

- `edited_localized_slides` gate + node helper widened to
  `{content, design, final_review}` (single owner: this ticket); constant
  and error copy renamed accordingly.
- Design ensure/re-render path (adds `validate_localized_slides` + fresh
  report storage — validation is absent there today).
- Feedback keying on send-back (target phase).

### REMOVED

- Silent no-op design revise path.

## Affected Areas

- Backend: `agents/carousel_workflow_nodes.py` (design node,
  `_edited_slide_updates`),
  `application/services/carousel/editorial_workflow_service_helpers.py`,
  `api/routes/carousels/editorial_workflow_routes_sanitize.py`,
  `domain/constants/carousel_workflow.py`
- Frontend: design step of `dashboard/create/[id]` (editor + send-back)
- Database: none (checkpoint-state only)
- API: resume request already carries the fields; design phase now honors them
- Tests: unit + `.feature` (behavior change); prod-shaped regression fixture
- Docs: workflow guide send-back matrix
- Prompts/LLM: content regeneration reuses existing prompts
- Observability: audit events for send-back include target phase
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: none
- Related: AE-0288, AE-0289, AE-0290, AE-0309, AE-0311

## Implementation Plan

1. Extract a target-phase routing helper shared with the AE-0288 path.
2. Widen the edited-slides gate + `_edited_slide_updates` to
   `{content, design, final_review}` with uniform apply + re-validate
   semantics; rename the content-only constant/error.
3. Implement the design send-back branch (reset content_approved, re-enter).
4. Add presentation validation to the design ensure/re-render path
   (store fresh report each execution).
5. Frontend: violation panel actions + inline editor + send-back dialog.
6. Regression fixture from the 38affb3e checkpoint shape; full gates.

## QA Checklist

- [ ] Security reviewed (edited copy sanitization preserves case, AE-0289)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (edits that do not fix violations; cap exhaustion)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-07-10

Ticket created from prod incident analysis (project 38affb3e dead-end loop).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

### 2026-07-10 (r5) — Cold-critic WARNs resolved: in-flight cap transition + revise never burns cap while blocking

Round-5: the corrected target-aware cap check is an accepted behavior
change for in-flight projects (documented; the uncapped edit path is the
safety valve). A plain design revise while a blocking report is present is
now cap-free and disabled in the UI — clicking it repeatedly can no longer
exhaust the design budget on a provable no-op.

### 2026-07-10 (r4) — Cold-critic WARN resolved: cap check/increment divergence acknowledged

Round-4 verified the cap check (reads current phase) and the send-back
increment (bumps target phase) already disagree on the existing
final_review→content path — this ticket's target-aware check is a fix to
a live bug, not just new-path plumbing, so the final_review path gets its
own regression coverage (Gherkin outline covers both source phases).

### 2026-07-10 (r3) — Cold-critic WARN resolved: guided recovery UX + uncapped edits

Round-3 flagged that re-interrupting with the same violations converts the
silent loop into a noisy one that burns the cap, with no defined escape
once caps are exhausted. Resolution: recovery actions are visually
dominant with an explanatory hint in the re-interrupt payload, and
`edited_localized_slides` submissions consume no revision cap (the cap
bounds LLM regeneration, not human edits) — so direct edits are the
always-available escape and no carousel can be cap-deadlocked.

### 2026-07-10 (r2) — Cold-critic WARN resolved: mechanism corrected + allowlist ownership

Round-2 review verified the design ensure re-renders unconditionally (no
`design_applied` skip exists) — the real gap is that it never runs
presentation validation; the Problem/Scope/Delta were rewritten so an
implementer targets the right code (add validation to the ensure, don't
hunt for a skip). This ticket now owns the full `edited_localized_slides`
allowlist widening to `{content, design, final_review}` (single shared
surface; AE-0314 depends on it), including the constant/error rename.
Open question answered: a still-blocking fresh report re-interrupts with
explicit recovery actions.

### 2026-07-10 — Cold-critic WARN resolved: revision-cap attribution pinned

External GLM 5.2 review flagged that "attributes the revise to the phase
that actually re-runs" asserted an outcome without defining the accounting.
Rule pinned: send-back increments the target phase's counter (content);
in-place edits and plain revises increment the current phase's (design).
The cap error names the charged phase so AE-0315's typed 409 can render
it. Gherkin scenario added.

## Blockers

None.

## Final Summary

Pending.
