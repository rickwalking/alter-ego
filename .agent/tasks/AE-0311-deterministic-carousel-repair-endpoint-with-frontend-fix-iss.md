# AE-0311 — Deterministic carousel repair endpoint with frontend fix-issues button

Status: Review
Tier: T2
Priority: High
Type: Feature
Area: cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-07-10
Updated: 2026-07-10

## Goal

Everything that was fixed by hand-run scripts in prod during the 2026-07
incidents becomes a first-class, client-callable capability: a single
authenticated endpoint runs the deterministic repairs against a carousel
(scaffold strip, body trim, canonical shape normalization, casing once
AE-0312 lands), updates **both** the workflow checkpoint state and the DB
projection, re-validates, and returns a before/after report. The frontend
shows a **"Fix issues automatically"** button wherever validation violations
are displayed, so the user can self-serve instead of needing operator SSH
surgery.

## Problem

Two prod incidents required manual intervention no user could perform:

- Project `38affb3e`: slide 4 stored the raw drafting scaffold as its body.
  The fix was a hand-written script editing LangGraph `checkpoint_blobs`
  (`localized_slides`, `slide_drafts`, `presentation_validation`) plus the
  `carousel_slides` row — all repairs that existing deterministic helpers
  (`presentation_review_repair`, `deterministic_repair_slide_payload`,
  `repair_body_length_and_heading`) can already compute, but that nothing
  exposes to the client.
- Project `66014ba3`: lowercase headings/"claude" fixed by hand-written SQL
  plus an in-container re-render.

The repair machinery exists server-side but is unreachable: no endpoint, no
UI. The user explicitly tried to fix things from the frontend and could not.

## Scope

- Backend: `POST /api/carousels/{project_id}/repair` (authenticated, owner
  or assigned reviewer):
  - Runs presentation validation on the current `localized_slides` (or
    persisted slides when the workflow is completed).
  - Applies the bounded deterministic repair pipeline per slide/locale:
    scaffold strip, heading-echo removal, body trim to policy budget,
    canonical shape normalization, and (once AE-0312 lands) casing repair.
  - Writes repaired values to **both** stores with an explicit two-commit
    contract (checkpoint saver and SQLAlchemy sessions cannot share one
    transaction — cold-critic verified): write the `carousel_slides`
    projection first in its own transaction, then the checkpoint via
    `aupdate_state`, then run a reconciliation check; on partial failure
    the endpoint reports which store was updated and the retry (idempotent)
    converges them. The consistency contract is documented in the endpoint
    docstring and asserted by a partial-failure test.
  - Concurrency guard is a **CAS, not a read**: the endpoint takes the same
    `bump_resume_lock_version` compare-and-swap the resume path uses before
    mutating, so a concurrent resume/run fails the CAS instead of racing
    (the bare `ensure_resume_not_in_progress` read is TOCTOU-vulnerable).
    (`bump_resume_lock_version` is a true atomic conditional UPDATE —
    verified in cold-critic r2 against `optimistic_lock_service`.)
    **Additionally** the repair acquires the per-project advisory lock
    from AE-0316's `carousel_project_lock` helper (session-scoped — held
    across BOTH commits of the two-commit contract, so the seam between
    the projection commit and the checkpoint write is inside the critical
    section), and AE-0316's resume-start guard rejects any resume
    submitted while the lock is held (`mutation_in_progress`) — so a
    resume can neither start during the seam nor read the half-committed
    state (cold-critic r6). The lock is the artifact-mutator
    serialization domain shared with AE-0313 and AE-0314, so a repair and
    a republish on the same (completed) project can never interleave (a
    republish must never render from half-repaired slides). The 409
    responses use AE-0316's typed conflict-detail schema.
  - All checkpoint writes go through `CarouselWorkflowEngine.update_state`
    (which infers `as_node` from the pending interrupt — cold-critic r5:
    a direct `_app.aupdate_state` risks the documented `as_node=None`
    interrupt-clearing footgun on approved-hold threads), sharing
    AE-0314's feasibility proof for parked threads.
  - Re-validates and writes the fresh `presentation_validation` report
    **in the same `aupdate_state` call** that writes the repaired copy —
    the checkpoint never holds repaired copy with a stale blocking report.
    Read-gap contract: between the projection commit and the checkpoint
    commit, state reads still serve the old stored report (the fast path
    returns it verbatim); the UI therefore re-fetches workflow state after
    a 200 from repair, and the response carries the fresh report so the
    client renders it without depending on the checkpoint read.
  - Returns `{repaired: [...per-slide diffs...], validation: report}`;
    HTTP 409 when the workflow is `in_progress` or the CAS fails.
  - Idempotent: a second call on repaired content is a no-op with a clean
    report.
- Backend: repairs are logged (`carousel_deterministic_repair_applied`) with
  project_id, slide indexes, and rule codes, and an audit event is emitted.
- Backend: **autonomous drift reconciliation** (cold-critic r3: "retry
  converges" assumed someone retries — a user who hits a 500 and closes
  the browser leaves split state forever). The workflow-workers tick
  detects projection↔checkpoint divergence for in-flight projects (fixed
  projection with a stale-blocking checkpoint report) and auto-converges
  it — the repair is idempotent by design — emitting
  `carousel_repair_drift_detected`/`_converged` events. Tick ordering
  with AE-0315's reaper is pinned there (reaper first; the reconciler's
  tick-owned convergence writes stamp the current `run_epoch`, so the
  fencing guard never rejects them). Authority rule:
  for **completed** projects the projection is authoritative (a
  projection-only success already serves correct PDFs; checkpoint lag is
  converged opportunistically); for **in-flight** projects the checkpoint
  is what the workflow reads, so convergence is required before the next
  phase — hence the autonomous reconciler, not just client retry.
- Frontend: a "Fix issues automatically" button rendered alongside any
  violation panel (content step, design step, and the publish page health
  card). On success it refreshes the workflow state/slides and shows the
  per-slide diff summary; on 409 it shows the run-in-progress state
  (AE-0315).
- For completed carousels, the response indicates when a republish is needed
  to propagate the fix into the served PDF, and the frontend chains the
  AE-0313 republish action (single user gesture).

## Non-Goals

- No LLM-based rewriting — deterministic transforms only.
- No new validation rules (casing rule itself is AE-0312).
- No artifact/PDF rebuild logic in this endpoint (AE-0313 owns republish;
  this ticket only chains to it from the UI).
- No repair of image assets.

## Acceptance Criteria

- [ ] `POST /api/carousels/{id}/repair` fixes a scaffold-contaminated slide
      (38affb3e regression fixture): body ≤ policy budget, no scaffold
      labels, no heading echo, canonical keys — in checkpoint state and in
      `carousel_slides`.
- [ ] Repair + re-validation clears a blocking `presentation_validation`
      report when all violations are deterministically repairable, and
      reports remaining violations when not.
- [ ] The endpoint returns 409 with a typed detail while the workflow run
      is `in_progress`, and is idempotent on already-clean content.
- [ ] The repair takes the `lock_version` CAS before mutating: a resume
      submitted concurrently with a repair loses the CAS (409) instead of
      racing — covered by a concurrency `.feature` scenario.
- [ ] Partial-failure convergence: if the process dies between the
      projection commit and the checkpoint update, re-invoking the repair
      converges both stores and the reconciliation check reports drift
      until it does (test kills the write between commits).
- [ ] The repaired copy and the fresh validation report land in ONE
      `aupdate_state` call (no checkpoint state ever holds repaired copy
      with a stale blocking report); the repair response carries the fresh
      report and the client re-fetches state after 200.
- [ ] Repair and republish (AE-0313) share the per-project advisory lock
      (AE-0316 helper): a concurrent repair + republish on the same
      project serialize (concurrency test).
- [ ] Drift left by a partial failure is detected and auto-converged by
      the watchdog tick without any client retry (test: kill between
      commits, run the tick, assert both stores converged and the drift
      events emitted).
- [ ] The frontend button appears with any violation panel, calls the
      endpoint, refreshes state, and renders the per-slide repair summary.
- [ ] For a completed carousel the UI chains repair → republish (AE-0313)
      so the served PDF reflects the fix without operator action.
- [ ] Authorization: only the owner/assigned reviewer can invoke it; audit
      event emitted per invocation.
- [ ] OpenAPI, route snapshot, and publishing snapshots regenerated (pinned
      artifacts).

## Gherkin Scenarios

```gherkin
Feature: One-click deterministic carousel repair

  Scenario: User repairs a scaffold-contaminated slide from the UI
    Given a carousel whose slide 4 body contains the raw drafting scaffold
    And the design step shows blocking presentation violations
    When the user clicks "Fix issues automatically"
    Then the repair endpoint strips the scaffold and trims the body
    And the checkpoint state and the slides projection both hold the repair
    And the violation panel clears after state refresh

  Scenario: Repair loses the race against a concurrent resume
    Given a repair request has passed the in-progress check
    And a resume request bumps the lock version before the repair mutates
    When the repair attempts its compare-and-swap
    Then the repair fails with 409 and mutates nothing

  Scenario: Repair is refused while a revision run is active
    Given the carousel workflow phase status is in_progress
    When the user clicks "Fix issues automatically"
    Then the endpoint responds 409 with a run-in-progress detail
    And the UI shows the revision-in-progress state

  Scenario: Unrepairable violations are reported honestly
    Given a slide whose violation cannot be fixed deterministically
    When the repair endpoint runs
    Then repairable violations are fixed and the rest are returned
    And the validation report reflects only the remaining violations
```

## Delta

### ADDED

- `POST /api/carousels/{project_id}/repair` route + application service
  wrapping the existing deterministic repair helpers.
- Checkpoint-state writer for repaired slides (single-owner, guarded
  against in-progress runs).
- Frontend "Fix issues automatically" button + repair summary UI.
- `carousel_deterministic_repair_applied` log + audit event.

### MODIFIED

- Violation panel components (content/design/publish) to host the button.

### REMOVED

- Nothing (manual prod scripts become obsolete, not deleted from history).

## Affected Areas

- Backend: new route in `api/routes/carousels/`, service in
  `application/services/carousel/` reusing `presentation_review_repair`
- Frontend: violation panel components, publish page health card
- Database: writes to `carousel_slides`; checkpoint tables via saver API
- API: new endpoint (OpenAPI + route snapshot regeneration required)
- Tests: unit + `.feature` (behavior change), 38affb3e regression fixture
- Docs: API reference; runbook note replacing manual repair recipe
- Prompts/LLM: none
- Observability: new log + audit events
- Deployment: none

## Dependencies

- Blocks: none
- Blocked by: AE-0316 (advisory lock + typed conflict details — hard
  dependency, defines the serialization domain), AE-0309 (shared
  fail-closed repair helpers), AE-0310 (the design-step button needs the
  design-step violation panel AE-0310 builds — the endpoint plus the
  content-step and publish-page buttons ship without it), AE-0312 (casing
  repair joins the pipeline when ready — endpoint ships without it)
- Related: AE-0310, AE-0313, AE-0286

## Implementation Plan

1. Service: gather state (checkpoint or completed projection), run bounded
   repair per slide/locale, compute diff report.
2. Guarded dual-write (checkpoint channel update + `carousel_slides`) with
   in-progress 409 guard reusing `ensure_resume_not_in_progress` semantics.
3. Route + schemas; regenerate pinned API artifacts.
4. Frontend button + summary; chain to AE-0313 republish for completed
   carousels.
5. Regression fixtures from both prod incidents; full gates.

## QA Checklist

- [ ] Security reviewed (authz, no path/state injection via project_id)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (mid-run 409, completed carousel, idempotency)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-07-10

Ticket created from prod incident analysis — codifies the manual repair
scripts run against projects 38affb3e and 66014ba3.

### 2026-07-10 — Developer implementation (all 8 deliverables)

Implemented endpoint + service (two-commit contract), drift reconciler,
policy threading, logging/audit, frontend button in all three panels + chained
republish, tests + Gherkin, and regenerated pinned artifacts. Gates green
(ruff/mypy/lint-imports/arch-ratchet backend; tsc/lint/vitest frontend).

Implementation notes / resolved ambiguities:
- **Drift reconciler validates, does not re-repair, the projection.** The
  projection is authoritative and (in the AE-0311 drift scenario) already
  repaired by the failed repair's projection-first commit; the reconciler
  converges the checkpoint only when the projection validates clean. A
  still-blocking projection is NOT drift (it needs the repair endpoint, not a
  checkpoint overwrite from stale copy).
- **Reconciler scope = parked (`awaiting_human`, non-completed) rows.** The
  reaper only flips `in_progress` rows, so the two never contend; a just-reaped
  row's checkpoint (reaper never touches checkpoint) is converged idempotently
  and epoch-fenced on a later tick, honouring the "after the reaper" ordering.
- **Frontend republish chaining via callback, not a cross-context import.** The
  button lives in the editorial context; importing publishing's
  `useRepublishCarousel` (barrel → cycle; concrete path → boundary violation).
  Resolved by the publish page supplying an `onRepublishNeeded` callback that
  owns the republish, keeping the button context-clean.
- **Deliverable 3 tested at the validation layer.** At the content gate the
  fail-closed chain auto-repairs repairable casing, so v2 warnings only surface
  when unrepairable; the behavior difference (v2 fires `proper_noun_casing` +
  `heading_not_sentence_case_pt`, v1 fires nothing) is asserted directly on
  `validate_localized_slides`, plus the resolve/thread plumbing unit tests.
- **Pre-existing branch failures:** 10 `test_editorial_workflow_resume_runner`
  tests fail on this branch independent of AE-0311 (reproduced with changes
  stashed) — out of scope for this ticket.

## Files Touched

### Backend — added
- `src/rag_backend/domain/constants/carousel_repair.py` — log/audit event + status constants.
- `src/rag_backend/application/services/carousel/carousel_repair_pipeline.py` — pure validate→repair→re-validate + per-slide diff.
- `src/rag_backend/application/services/carousel/carousel_repair_projection.py` — localized ↔ `carousel_slides` mapping.
- `src/rag_backend/application/services/carousel/carousel_repair_service.py` — two-commit contract (lock + CAS + projection-first + one-call checkpoint + audit).
- `src/rag_backend/api/schemas/carousel_repair.py` — response schema.
- `src/rag_backend/api/routes/carousels/repair.py` — `POST /api/carousels/{id}/repair`.
- `src/rag_backend/infrastructure/database/carousel_drift_reconciler.py` — autonomous drift reconciler.
- `src/rag_backend/bootstrap/carousel_drift_reconciler_factory.py` — engine-checkpoint gateway + reconciler factory.

### Backend — modified
- `api/routes/carousels/router.py` — mount repair router.
- `api/routes/carousels/deps.py` — `get_carousel_repair_service` (shares the cached `get_db` session; reuses the workflow service's events + baselined repo → no new api→infra edge).
- `application/services/carousel/editorial_workflow_service.py` — `update_workflow_state` + `events` property; **deliverable 3**: thread the project's `presentation_policy_version` into workflow-start seeding.
- `application/services/carousel/phase_artifact_runner.py` — **deliverable 3**: `_state_policy_version` → `ContentReviewContext.policy_version` → `FailClosedReviewCommand.policy_version`.
- `domain/protocols/carousel_run.py` — `CarouselCheckpointStateGateway` + `CarouselDriftReconciler` protocols.
- `application/workers/workflow_workers.py` — drift reconciler runs AFTER the reaper (AE-0315 ordering hook).
- `bootstrap/app_factory.py` — build + inject the reconciler.
- Regenerated pinned artifacts: `docs/architecture/openapi.json`, `backend/tests/snapshots/openapi_routes.json`.

### Frontend — added
- `src/modules/editorial/workspace/hooks/use-repair-carousel.ts` — repair mutation hook + zod schema.
- `src/modules/editorial/workspace/components/auto-repair-button.tsx` — "Fix issues automatically" button (diff summary, typed-409 banner path, republish chaining via callback).
- `*.test.tsx` for the button + `create-phase-review` wiring.

### Frontend — modified
- `constants/api.ts` — `CAROUSEL_REPAIR`.
- `create-phase-review.tsx` (+ `create-workflow-panel.tsx`) — render the button at content + design steps.
- `app/dashboard/create/[id]/publish/page.tsx` — button near `RebuildPdfSection`, chains `useRepublishCarousel`.
- `modules/editorial/index.ts`, `workspace/components/types.ts` — exports + colocated props type.
- `i18n/locales/{en,pt}.json` — `editorialWorkflow.review.autoRepair`.

### Gherkin
- `tests/features/carousel_deterministic_repair.feature`.

## Test Evidence

- Backend AE-0311 suite (pipeline + projection + service + policy-threading + drift): `uv run pytest ... -q` → **25 passed**.
- Full backend unit: `uv run pytest tests/unit -q` → **2360 passed, 1 skipped, 10 failed**. The 10 failures are all `test_editorial_workflow_resume_runner.py::TestExecuteBackgroundResume::*` and are **pre-existing on the branch** (reproduced with AE-0311 changes fully stashed) — not caused by this ticket.
- `ruff format`/`ruff check src/ tests/` → All checks passed.
- `mypy rag_backend/ --explicit-package-bases` (MYPYPATH=src) → **no issues in 569 files**.
- `lint-imports` → 22 kept, 0 broken. `import_baseline.py --check` → **PASS** (api→infra held at baseline 77; application→infra ratcheted DOWN to 60).
- OpenAPI + route snapshot regenerated (repair route + schemas present).
- Frontend: `tsc --noEmit` exit 0; `npm run lint` (full chain incl. circular/boundaries/component-types/i18n/dup) exit 0; `vitest run` over touched areas → **316 passed** (incl. 6 new).

## QA Report

Pending.

## Decision Log

### 2026-07-10 (r6) — Cold-critic BLOCKER resolved: seam closed via resume-start guard

Round-6 proved the CAS alone lets a fresh-versioned resume start inside
the two-commit seam and regenerate from a stale checkpoint. Resolution:
AE-0316's resume-start guard (non-blocking advisory-lock check → typed
409) blocks resume starts for the lock's whole hold window; the CAS
remains the stale-client guard. The CAS's atomicity (single conditional
UPDATE) is stated as verified fact.

### 2026-07-10 (r5) — Cold-critic findings resolved: engine wrapper + session lock span

Round-5: checkpoint writes routed through the engine's `update_state`
wrapper (as_node inferred — avoids the interrupt-clearing footgun on
approved-hold threads, sharing AE-0314's proof); the advisory lock is
session-scoped and held across both commits so the two-commit seam is
inside the critical section; reconciler-vs-reaper tick ordering mirrored
from AE-0315.

### 2026-07-10 (r3) — Cold-critic WARN resolved: autonomous drift reconciliation + AE-0316

Round-3: "retry converges" relied on a client retry nobody guarantees.
Added the watchdog-tick drift reconciler (auto-converge, idempotent, with
drift events) and pinned the authority rule per project status (completed
→ projection authoritative; in-flight → checkpoint must be converged
before the workflow reads it). The advisory lock and typed 409 schema are
now consumed from AE-0316 (hard blocked-by), pinning the build order the
critic asked for.

### 2026-07-10 (r2) — Cold-critic WARN resolved: read-gap + shared lock with republish

Round-2 review flagged (1) a mid-window read gap — the state read fast
path returns the stored validation verbatim, so between the two commits
the client could see stale violations over fixed rows; and (2) that the
repair's `lock_version` CAS and AE-0313's build advisory lock were
disjoint domains, letting repair and republish interleave. Resolution:
the repaired copy + fresh validation land in one `aupdate_state` call,
the repair response carries the fresh report and the UI re-fetches after
200 (read-gap contract documented), and the repair acquires the same
per-project advisory lock as republish (the repair-vs-republish
serialization; resume/reap coordination is via the lock_version CAS per
AE-0316's domain contract).

### 2026-07-10 — Cold-critic BLOCKER resolved: non-atomic dual-write + TOCTOU guard

External GLM 5.2 review (`.agent/reports/ae0309-0315.skeptical-review.md`)
verified that checkpoint saver and SQLAlchemy sessions cannot share a
transaction and that `ensure_resume_not_in_progress` is a TOCTOU read.
Resolution adopted (critic mitigations a+b+c): explicit two-commit contract
(projection-first, then `aupdate_state`, then reconciliation; idempotent
retry converges), repair takes the `lock_version` CAS before mutating, and
a concurrency `.feature` scenario is now an AC. "Same operation" wording
removed — it was aspirational, not a contract.

### 2026-07-10 — Cold-critic WARN resolved: design-step button ordering

The design step renders no violation panel today; the design-step button is
now explicitly blocked by AE-0310. Endpoint + content/publish buttons ship
independently.

## Blockers

None.

## Final Summary

Pending.
