# AE-0314 — Frontend flow to edit carousel text without regenerating images

Status: Ready
Tier: T2
Priority: High
Type: Feature
Area: frontend
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-07-10
Updated: 2026-07-10

## Goal

The backend capability shipped recently — going back on workflow state and
changing slide text **without regenerating images** (edited localized slides
+ outline-heading-hash image preservation) — becomes usable from the client.
A user who spots a typo or casing issue at any review step, or even after
completion on the publish page, can edit the text in place and see it in the
final PDF, never triggering image regeneration and never needing operator
access.

## Problem

The backend accepts `structured_feedback.edited_localized_slides` on resume
— but **only at the content phase today**: the HTTP gate rejects edited
slides for any other checkpoint phase
(`ERR_EDITED_SLIDES_CONTENT_PHASE_ONLY`), and `_edited_slide_updates`
short-circuits to `{}` off-content. AE-0310 widens the allowlist to
`{content, design, final_review}` in one place; this ticket consumes that
widened surface. The backend also preserves
generated images across content send-backs via outline-heading hashing. But
the current frontend exposes **none of it**:

- No slide text editor at the review steps — the only affordances are
  approve / revise-with-feedback, and free-text feedback triggers a full
  LLM regeneration pass (~15 min, AE-0315) even for a one-character fix.
- No path at all once the carousel is completed. Prod incident 66014ba3:
  the user saw lowercase headings on the **publish page**, tried to fix
  them in the UI, could not, and the fix required manual SQL + an
  in-container re-render.

The user's explicit requirement: capabilities must exist on the client
side, not only as backend features.

## Scope

- Review-step editor — phased by backend support: **content ships first**
  (the only phase whose edit path exists today); the design and
  final_review editors activate once AE-0310 lands the widened
  `{content, design, final_review}` allowlist (hard dependency — the
  final_review editor MUST NOT ship against the current gate, which 422s
  it). The editor semantics per phase (apply edits → re-validate) are
  owned by AE-0310; this ticket owns the UI:
  - Each slide card gets an "Edit text" affordance opening an inline editor
    for heading/body (and summary/closing extras fields) in both locales.
  - Saving submits the resume with `edited_localized_slides` (no free-text
    feedback), preserving markdown emphasis and case (AE-0289 semantics).
  - Client-side validation preview against the policy budgets (max body
    length, scaffold labels) before submit; server report rendered on
    rejection.
  - The UI states clearly that text edits do not regenerate images.
- Post-completion editor (publish page):
  - "Edit text" on each slide opens the same editor; saving calls a
    backend slide-update endpoint for completed projects (update
    `carousel_slides` + extras translations under the existing write-owner
    guard **and holding AE-0316's per-project advisory lock** — the
    endpoint is the third member of the serialization domain, so an edit
    can never lose an update to a concurrent repair or race a republish
    render), then chains the AE-0313 republish so the served PDF reflects
    the edit — one user flow: edit → save → rebuild → fresh PDF.
    **The republish is server-guaranteed, not a client obligation**
    (cold-critic r6: a browser closed between the edit 200 and the
    republish call would leave corrected text with a stale public PDF —
    the 66014ba3 incident reskinned): the edit endpoint sets a persisted
    `needs_republish` marker in the same transaction as the slide write;
    the frontend triggers the republish immediately for fast feedback,
    and the watchdog tick performs any pending marked republish older
    than a few minutes as the guarantee. The publish page renders a "PDF
    rebuild pending" state while the marker is set.
  - Blocked with a clear message while a workflow run is in progress.
  - **Source-of-truth rule (pinned; cold-critic finding, corrected r2):**
    for `completed` projects the `carousel_slides` projection is canonical.
    `resolve_presentation_review_from_state`'s fast path returns the
    **stored** checkpoint `presentation_validation` verbatim (it only
    re-derives when no stored report exists), so a projection-only edit
    leaves the stored stale report being served over fixed copy. **Decision
    (made at plan time, not implementation time): option (a)** — the
    completed-project edit endpoint also writes the edited copy and a
    freshly computed validation report to the checkpoint via
    `aupdate_state`. Premise corrected by cold-critic r3: approved
    carousels deliberately do NOT reach END — the graph parks at the
    `approved_hold_phase` interrupt precisely so they stay resumable
    (`carousel_workflow.py` constants; `approved_hold_phase` node), and
    `aupdate_state` on a parked/interrupted thread is the already-used
    pattern in this codebase. **Pre-implementation proof remains task #1**:
    an integration test edits a real approved-hold thread via
    `aupdate_state` and asserts (i) the write lands, (ii) the pending
    interrupt is preserved (the documented `as_node` footgun in
    `carousel_workflow_engine.py:110-114` is explicitly asserted against).
    **Fallback for legacy END-state threads** (projects finalized before
    the hold-phase design): the **projection-only path is the explicit
    design** — cold-critic r4 refuted the `Command(goto=...)` re-park
    idea (that recovery requires `snapshot.next` empty AND
    `phase_status=awaiting_human`, targets `current_phase`, and no
    `goto=approved_hold` path exists; approved END threads have
    `phase_status=approved`, so it is unreachable). For such threads the
    edit writes the projection, the republish serves the corrected PDF
    (it renders from `carousel_slides`), and the stale checkpoint report
    is converged/suppressed by AE-0311's drift reconciler — which is
    therefore a **hard dependency** of the post-completion flow, not a
    nice-to-have. Option
    (b) (status-aware read derivation) was rejected for blast radius: it
    changes read semantics for ALL completed projects, edited or not.
    Decision to be recorded in
    the AE-0293 read-authority ADR; a test asserts post-edit
    `presentation_validation` reflects the edited copy.
- Shared component: one slide-text editor used by review steps and publish
  page (per component-reuse standards), i18n'd (pt-BR/en).

## Non-Goals

- No image regeneration or image-prompt editing.
- No outline restructuring (adding/removing/reordering slides).
- No LLM-assisted rewriting from the editor (deterministic user input only).
- No design-step enablement (AE-0310) or deterministic auto-repair
  (AE-0311) — this ticket is the manual-edit path.

## Acceptance Criteria

- [ ] At content and final_review steps, a user can edit a slide's heading
      and body (both locales) and submit; the workflow state reflects the
      edit and images are not regenerated (image assets unchanged,
      verified in test).
- [ ] Editing text on a summary/closing slide edits its structured extras
      fields (summary points, closing features), not just heading/body.
- [ ] On a completed carousel, the publish page edit flow persists the
      change and chains republish (AE-0313); the downloaded PDF contains
      the edited text with unchanged images.
- [ ] After a completed-project edit, the `presentation_validation`
      returned to the client reflects the edited copy — no stale
      checkpoint-derived violations over fixed content (test covers a
      previously-blocking violation fixed by the edit).
- [ ] Feasibility proof precedes feature code: the
      `aupdate_state`-on-approved-hold-thread integration test exists and
      passes (write lands, pending interrupt preserved) before any editor
      UI or endpoint work is merged; the legacy END-thread fallback is
      covered by its own test or an explicit documented waiver.
- [ ] Markdown emphasis and letter case survive the round-trip
      (AE-0289 regression covered in the UI path).
- [ ] Client-side budget validation warns before submit; server-side
      violations render in the editor.
- [ ] Editor is blocked with a clear state while `phase_status` is
      `in_progress`.
- [ ] The completed-project slide-update endpoint holds the AE-0316
      advisory lock for its full write sequence; a concurrent repair on
      the same project serializes (concurrency test).
- [ ] Republish guarantee: an edit whose client never calls republish
      still converges — the watchdog performs the marked republish and
      clears the marker (test); the publish page shows the pending state
      until then.
- [ ] i18n complete for pt-BR/en; component reused across steps (no
      duplicated editor implementations).

## Gherkin Scenarios

```gherkin
Feature: Edit carousel text without regenerating images

  Scenario: Fix a typo at the final review step
    Given a workflow awaiting human review at final_review
    When the user edits slide 1's heading in the inline editor and saves
    Then the resume carries edited_localized_slides for slide 1
    And the workflow state shows the corrected heading
    And no image generation occurs

  Scenario: Fix casing on a completed carousel from the publish page
    Given a completed carousel whose slide 1 heading starts lowercase
    When the user edits the heading on the publish page and saves
    Then the slide row is updated and a republish is triggered
    And the new PDF contains the corrected heading with unchanged images

  Scenario: Over-budget edit is caught before submission
    Given the policy limits slide bodies to 220 characters
    When the user types a 300-character body in the editor
    Then the editor shows the budget violation before submit is enabled

  Scenario: Editing is unavailable during an active revision run
    Given the workflow phase status is in_progress
    When the user opens a slide on the review step
    Then the edit affordance is disabled with a run-in-progress message
```

## Delta

### ADDED

- Shared slide-text editor component (frontend).
- Review-step wiring to `edited_localized_slides` resume submission.
- Backend slide-update endpoint for completed projects (heading/body/extras
  translations) + publish-page wiring chaining AE-0313 republish.

### MODIFIED

- Slide cards at review steps and publish page (edit affordance).

### REMOVED

- Nothing.

## Affected Areas

- Backend: slide-update endpoint for completed projects (write-owner
  guarded); the review-step edit path's gate/node widening is owned by
  AE-0310 (this ticket makes NO independent workflow-node changes but
  depends on AE-0310's)
- Frontend: create-flow review steps, publish page, shared editor component
- Database: `carousel_slides` updates via existing write owner
- API: new completed-project slide-update endpoint (pinned artifacts
  regeneration); resume payload unchanged
- Tests: unit + `.feature` (behavior change); Playwright e2e for the two
  main flows
- Docs: user-facing publish flow guide
- Prompts/LLM: none
- Observability: audit event for post-completion slide edits
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: AE-0316 (advisory lock for the slide-update endpoint),
  AE-0313 (publish-page flow needs republish to propagate),
  AE-0310 (design + final_review editors need the widened
  `edited_localized_slides` allowlist — the content editor is unblocked),
  AE-0311 (the post-completion flow's partial-failure safety depends on
  the drift reconciler — a projection-committed/checkpoint-failed edit
  must be converged autonomously, and legacy END threads rely on it for
  stale-report suppression)
- Related: AE-0310 (design-step editor), AE-0311 (auto-repair button),
  AE-0289 (case-preserving sanitization), AE-0290 (edited-slides phase
  semantics)

## Implementation Plan

1. Build the shared editor component (locales, budgets, markdown-safe).
2. Wire review steps to submit `edited_localized_slides`; verify image
   assets untouched in integration test.
3. Backend endpoint for completed-project slide updates + audit event;
   regenerate pinned API artifacts.
4. Publish-page flow chaining republish; cache-busted refresh.
5. Playwright e2e for both flows; full gates.

## QA Checklist

- [ ] Security reviewed (authz on slide updates; sanitization preserves
      case without allowing markup injection)
- [ ] XSS boundary named and verified: every render path for slide copy
      (editor preview, review cards, publish page, violation panels) uses
      the sanitized markdown renderer — no `dangerouslySetInnerHTML` on
      raw copy; a stored-XSS payload test (`<img onerror>`,
      `[x](javascript:)`) renders inert
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (summary/closing extras, EN-only edit, concurrent
      run lock)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-07-10

Ticket created from prod incident analysis (project 66014ba3: user could
not fix slide text from the frontend at publish; backend capability exists
but is unexposed).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

### 2026-07-10 (r6) — Cold-critic WARN resolved: server-guaranteed republish

Round-6: frontend-only chaining left a browser-close gap (edit lands,
PDF stays stale). The edit now persists a `needs_republish` marker
transactionally; the watchdog guarantees the republish if the client
never triggers it, and the publish page surfaces the pending state.

### 2026-07-10 (r4) — Cold-critic WARNs resolved: goto fallback dropped; AE-0311 hard dependency

Round-4 refuted the `Command(goto=...)` re-park fallback (unreachable for
approved END threads — the gate-reopen path requires awaiting_human and
never targets approved_hold). The projection-only path is now the explicit
legacy design, and AE-0311 moved from Related to Blocked-by: its drift
reconciler is what makes a partial post-completion edit (projection
committed, checkpoint write failed) converge without manual intervention.

### 2026-07-10 (r3) — Cold-critic BLOCKER resolved: END-thread premise corrected

Round-3 review verified the codebase deliberately avoids END: approved
carousels park at the `approved_hold_phase` interrupt to stay resumable.
The r2 wording ("END-state thread") was wrong in a way that helps —
`aupdate_state` on a parked thread is the already-used pattern. Resolution:
premise rewritten; feasibility test now targets a real approved-hold
thread and asserts interrupt preservation (the `as_node` footgun); legacy
END-state threads get a documented fallback (`ainvoke(Command(goto=...))`
re-park, or projection-only with drift alert). Feasibility-before-feature
is now an explicit AC.

### 2026-07-10 (r2) — Cold-critic BLOCKER resolved: final_review edit path does not exist

Round-2 review verified the premise "backend accepts edited slides at
content/final_review" was false — the gate 422s off-content and the node
helper short-circuits. Resolution: AE-0310 now owns the coherent allowlist
widening to `{content, design, final_review}`; this ticket is blocked by it
for the design/final_review editors, ships the content editor and
publish-page flow independently, and no longer claims "no workflow-node
changes". Resolver claim corrected (fast path returns stored report
verbatim); source-of-truth option (a) decided at plan time with an
`aupdate_state`-on-END-thread feasibility test as the first implementation
task. XSS render boundary added to QA.

### 2026-07-10 — Cold-critic WARN resolved: completed-edit validation staleness

External GLM 5.2 review verified `resolve_presentation_review_from_state`
re-derives validation from checkpoint state on every read, so a
projection-only completed-project edit would show stale violations over
fixed content. Resolution: source-of-truth rule pinned in scope (projection
canonical for `completed`; endpoint updates checkpoint or derivation is
status-aware), decision to be recorded in the AE-0293 read-authority ADR,
post-edit validation AC added.

## Blockers

None.

## Final Summary

Pending.
