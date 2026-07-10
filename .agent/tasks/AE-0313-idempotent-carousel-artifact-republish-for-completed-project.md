# AE-0313 — Idempotent carousel artifact republish for completed projects

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

Re-finalizing a **completed, already-versioned** carousel works first try:
one endpoint re-renders slides/PDFs from the persisted slide data, builds a
new content-addressed artifact version, and atomically activates it — and
the frontend publish page has a "Rebuild PDF" action that calls it. Slide
data fixed after completion (AE-0311 repair, AE-0314 text edits) propagates
into the served PDF without operator access.

## Problem

Prod incident (project `66014ba3`, 2026-07-10): after fixing slide text in
`carousel_slides`, propagating the fix into the served PDF was broken twice
over:

1. **No client path that re-renders without a forced layout change and
   builds a new artifact version.** `re_render_slides` is reachable from
   the completed-gated strategy endpoint (`PUT /carousels/{id}/strategy`),
   but that forces a layout-strategy change and does not build/activate a
   version; `export_and_complete_carousel` is only invoked by the
   images-approval finalize. The prod fix required running both
   in-container by hand. (Scope must not duplicate or conflict with the
   existing strategy endpoint — the new endpoint is the no-strategy-change,
   versioned republish.)
2. **Re-finalize on a versioned project is buggy.** `export_and_complete_carousel`
   re-renders into the plain `pt/`/`en/` dirs, but `_verify_artifacts` →
   `_pdf_check` → `_safe_output_file` resolves against the **old versioned
   serving root** (because `project.artifact_version` is set), rejects the
   fresh plain-path PDFs as outside it, reports "pt PDF missing; en PDF
   missing", and — worse — `mark_failed`s a healthy completed project. The
   manual workaround was clearing `artifact_version` + resetting status
   before re-running.

## Scope

- Backend bugfix: during finalize, `_verify_artifacts` must validate the
  **freshly rendered pre-promotion outputs** (project root), never the
  previously active version root. `_pdf_check`'s `_safe_output_file`
  confinement should be evaluated against the directory the render just
  wrote to.
- Backend bugfix: a failed re-finalize on a completed project must not
  `mark_failed` the project — it stays `completed` on its current artifact
  version, and the error is returned to the caller.
- Backend: `POST /api/carousels/{project_id}/republish` (authenticated,
  owner/assigned reviewer, only for `completed` projects):
  - Runs the full finalize pipeline (re-render from persisted slides →
    health-check fresh outputs → `build_and_activate` a new version →
    update `current.json`, `artifact_version`, `pdf_path`/`pdf_path_en`).
  - Idempotent: unchanged slide data reproduces the same content digest and
    re-activates it — safe to click twice. **Known gap to fix (cold-critic
    r3, code-verified):** `_activate_existing` today runs the DB CAS and
    stamps `artifact_version` but does NOT call `write_current_index`, so
    the on-disk `current.json` lags the DB until a lazy read-path
    reconciler runs. This ticket adds the `write_current_index` call to
    `_activate_existing` so `current.json` reflects the re-activated
    version immediately after the 200 (a user who republishes and
    downloads without an intervening state read must get the right PDF).
    **And the fresh-build path is reordered** (cold-critic r4: today
    `write_current_index` runs BEFORE the `activate_build` CAS — a CAS
    loss leaves `current.json` pointing at a version that never activated
    in the DB, the inverted drift): in both paths the index write happens
    only **after** the DB activation commit succeeds, inside the advisory
    -lock critical section.
  - 409 with a typed detail when a workflow run or another build is in
    flight. Concurrent-build serialization is **net-new** (cold-critic
    verified there is no lock/CAS around `build_and_activate` today —
    content addressing dedupes outputs, but two concurrent builds could
    both flip `current.json`/`artifact_version`): add a per-project
    advisory lock — consumed from AE-0316's `carousel_project_lock`
    helper, the single shared serialization domain with AE-0311's repair
    (a republish can never render from half-repaired slides). **Lock scope
    pinned:** acquired at `build_and_activate` entry (before digest
    computation) and released after the DB commit — never narrower, so
    the digest/manifest computation, `write_current_index`, and the CAS
    all sit inside one critical section.
  - Pin the status invariant: define (and assert in a test) what
    `phase_status` a `completed` carousel may hold; republish rejects when
    a workflow run is active on the project so republish and resume can
    never mutate concurrently.
- Frontend: publish page gets a "Rebuild PDF" action (with confirmation)
  that calls the endpoint, shows build progress/result, and busts cached
  PDF/slide URLs on success (artifact version in the query string or path).
- Frontend: after an AE-0311 repair on a completed carousel, the UI offers
  the republish as the follow-up step (single flow).

## Non-Goals

- No changes to first-time finalize behavior after images approval (beyond
  the shared health-check fix).
- No slide text editing (AE-0314) or deterministic copy repair (AE-0311).
- No artifact version garbage collection / retention policy.
- No layout-strategy changes (existing endpoint already covers that).

## Acceptance Criteria

- [ ] Re-finalizing a completed project with `artifact_version` set
      succeeds: new version dir, `current.json` flipped, `pdf_path` points
      into the new version, project stays `completed` (regression test
      reproducing the 66014ba3 failure).
- [ ] A failed republish leaves the project `completed` on its prior
      artifact version with `error_message` untouched.
- [ ] `POST /api/carousels/{id}/republish` is exposed, auth-guarded,
      rejects non-completed projects (409/422 typed detail), and is
      idempotent on unchanged content (same digest re-activated).
- [ ] Two concurrent republish invocations serialize on the per-project
      build lock: exactly one activation wins per digest and
      `current.json`/`artifact_version` are never interleaved (concurrency
      test).
- [ ] `_activate_existing` writes `current.json`: immediately after an
      idempotent republish 200, the on-disk index names the re-activated
      version with no read-path reconciliation required (test).
- [ ] Fresh-build ordering: `write_current_index` executes only after a
      successful `activate_build` commit; a CAS-losing concurrent build
      never touches `current.json` (test seeds a CAS conflict and asserts
      the index still names the winner).
- [ ] Digest determinism (cold-critic r5): the artifact version
      fingerprint hashes slide/manifest **data**, never rendered PDF/JPG
      bytes (which embed timestamps) — regression test proves two renders
      of identical slide data yield the identical digest, making
      repeat-republish a true no-op instead of unbounded version growth.
- [ ] The `completed`↔`phase_status` invariant is pinned by a test, and
      republish is refused while a workflow run is active on the project.
- [ ] First-time-finalize regression: a first finalize on a project with a
      stale `artifact_version` left by a prior partial run passes the
      health check against the freshly rendered outputs (the shared
      health-check fix must not regress the images-approval finalize).
- [ ] Call-site matrix (cold-critic r6): every caller of
      `_verify_artifacts`/`_safe_output_file` is enumerated and covered
      by a test per (call site × artifact_version state: NULL, set,
      stale) — the shared-function change is proven safe for both the
      republish path and the primary images-approval finalize.
- [ ] Publish page "Rebuild PDF" action works end-to-end: after a slide
      text fix, the downloaded PDF contains the new text without any
      operator intervention.
- [ ] Served PDF/slide URLs are cache-busted on version change.
- [ ] OpenAPI + route snapshot + publishing snapshots regenerated.

## Gherkin Scenarios

```gherkin
Feature: Republish a completed carousel's artifacts

  Scenario: Republish after a slide text fix
    Given a completed carousel with an active artifact version
    And its slide copy was corrected after completion
    When the user clicks "Rebuild PDF" on the publish page
    Then slides and PDFs re-render from the persisted slide data
    And a new artifact version is built and activated
    And the downloaded PDF contains the corrected copy

  Scenario: Health check validates fresh outputs, not the old version root
    Given a completed carousel with an active artifact version
    When the republish pipeline health-checks the re-rendered outputs
    Then it validates the files the render just wrote
    And it does not report the fresh PDFs as missing

  Scenario: Failed republish never corrupts a completed project
    Given a completed carousel
    When the republish pipeline fails during artifact build
    Then the project status remains completed
    And the previously active artifact version keeps serving

  Scenario: Republish with unchanged content is a safe no-op
    Given a completed carousel republished moments ago
    When the user clicks "Rebuild PDF" again
    Then the existing content digest is re-activated without error

  Scenario: Concurrent republishes serialize on the build lock
    Given two republish requests arrive for the same project concurrently
    When both reach the artifact build
    Then the second waits on or is rejected by the per-project build lock
    And current.json reflects exactly one coherent activation
```

## Delta

### ADDED

- `POST /api/carousels/{project_id}/republish` route + handler delegating to
  the finalize pipeline.
- Publish-page "Rebuild PDF" action with progress/result UI and
  cache-busting.

### MODIFIED

- `_verify_artifacts` / `_pdf_check` to validate pre-promotion outputs.
- Finalize failure handling on completed projects (no `mark_failed`).

### REMOVED

- Nothing.

## Affected Areas

- Backend: `application/services/carousel/editorial_finalize.py`,
  `artifact_health.py`, `artifact_path_resolver.py`, new route in
  `api/routes/carousels/`
- Frontend: publish page (`dashboard/create/[id]/publish`)
- Database: `carousel_projects.artifact_version` / pdf paths (existing
  columns); `carousel_artifact_builds` records
- API: new endpoint (pinned artifacts regeneration)
- Tests: unit + `.feature` (behavior change); 66014ba3 regression fixture
- Docs: publish flow guide; replaces the manual re-render runbook recipe
- Prompts/LLM: none
- Observability: existing `carousel_artifact_promoted` logging covers it
- Deployment: none

## Dependencies

- Blocks: AE-0314 (post-completion edits need republish to propagate)
- Blocked by: AE-0316 (per-project lock helper + typed conflict details)
- Related: AE-0311 (repair chains into republish), AE-0121 (artifact build
  facade), AE-0107 (write owner)

## Implementation Plan

1. Fix `_verify_artifacts` output-dir resolution (validate fresh renders);
   regression test with `artifact_version` set.
2. Guard `mark_failed` on completed projects in the finalize error paths.
3. Add republish route + schemas; regenerate pinned API artifacts.
4. Publish-page action + cache-busting by artifact version.
5. End-to-end test: edit slide row → republish → assert new version dir +
   `current.json` + pdf paths; full gates.

## QA Checklist

- [ ] Security reviewed (authz; no rebuild of other users' projects)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (concurrent build CAS conflict, digest reuse,
      missing output_dir)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-07-10

Ticket created from prod incident analysis (project 66014ba3: PDF served
stale versioned artifact after slide fix; re-finalize health check false
negative marked the project failed).

### 2026-07-11 — Developer implementation (all 10 deliverables)

- Health-check fix: `CarouselArtifactHealthRequest.validate_pre_promotion`
  routes `evaluate_carousel_artifacts` to the project-root fresh outputs and
  skips the stale-version manifest check; `_verify_artifacts` sets it. 66014ba3
  regression + full call-site matrix (NULL/set/stale × pre_promotion) covered.
- Failure safety: `_fail_finalize` skips `mark_failed`/persist when the project
  is already `completed` (error returned, prior version + error_message intact).
- Build ordering: `write_current_index` moved AFTER the `activate_build` commit
  in the fresh path; `_activate_existing` now writes the index too (idempotent
  path no longer lags the DB). A CAS-losing build never touches current.json.
- New `POST /api/carousels/{id}/republish`: owner/assigned-reviewer auth, 422 on
  non-completed, typed `run_in_progress` 409 when a run is active, shared
  advisory lock (AE-0316) held across the whole pipeline and surfaced as
  `build_in_progress` for concurrent builds. Reads the refreshed session-identity
  project (no new api→infrastructure edge).
- Frontend: publish-page "Rebuild PDF" action (NeonModal confirmation) → republish
  hook → progress/result + version cache-busting on PDF/slide URLs; pt/en i18n.
- Regenerated route snapshot + `docs/architecture/openapi.json` (publishing
  snapshots unaffected — full unit suite green).

## Files Touched

Backend (src):
- `application/services/carousel/artifact_health.py` — `validate_pre_promotion`
  + `_health_root`.
- `application/services/carousel/editorial_finalize.py` — `_fail_finalize`
  guard; pre-promotion health request.
- `application/services/carousel/artifact_build_service.py` — index-write
  ordering (both paths) + `project_root` in `ActivateExistingCommand`.
- `application/services/carousel/carousel_republish.py` — NEW orchestration +
  `republish_build_lock` (mutation→build_in_progress) + `engine_from_session`.
- `api/routes/carousels/republish.py` — NEW route; `api/routes/carousels/router.py`
  wiring; `api/schemas/carousel.py` `CarouselRepublishResponse`.
- `domain/constants/carousel_republish.py` — NEW constants.

Backend (tests):
- `tests/unit/application/test_artifact_health_pre_promotion.py` (NEW, 5),
  `test_carousel_republish.py` (NEW, 6), `tests/unit/api/test_republish_route.py`
  (NEW, 7); additions to `test_artifact_build_service.py` (+4) and
  `test_editorial_finalize.py` (+2); `tests/features/carousel_republish.feature`
  (NEW).

Frontend:
- `constants/api.ts` (`CAROUSEL_REPUBLISH`);
  `modules/publishing/distribution/hooks/use-republish-carousel.ts` (NEW);
  `modules/publishing/distribution/components/rebuild-pdf-section.tsx` (NEW) +
  test; `publish-panel.tsx` + `types.ts` (cacheBustToken); publishing +
  distribution barrels; `app/dashboard/create/[id]/publish/page.tsx`;
  `i18n/locales/{en,pt}.json` (`publish.rebuildPdf`).

Artifacts: `docs/architecture/openapi.json`, `backend/tests/snapshots/openapi_routes.json`.

## Test Evidence

- `MYPYPATH=src uv run mypy -p rag_backend` → Success: no issues found in 590 source files.
- `uv run ruff check src/rag_backend tests/...` → All checks passed!
- `uv run lint-imports` → Contracts: 22 kept, 0 broken.
- `uv run pytest tests/unit -q` → 2300 passed, 1 skipped.
- New backend files: `test_carousel_republish.py` (6), `test_republish_route.py`
  (7), `test_artifact_health_pre_promotion.py` (5) all green.
- Frontend: `npx tsc --noEmit` clean; `npm run lint` EXIT=0; vitest
  `rebuild-pdf-section.test.tsx` (4) + `publish-panel.test.tsx` (10, incl. new
  cache-bust) green; schema-drift: No drift across mapped schemas.

## QA Report

Pending.

## Decision Log

### 2026-07-10 (r5) — Cold-critic WARN resolved: digest determinism pinned

Round-5: the idempotency AC now rests on an explicit, tested property —
the version fingerprint hashes slide/manifest data (not rendered bytes,
which embed timestamps). Two renders of identical data must produce the
identical digest.

### 2026-07-10 (r4) — Cold-critic WARN resolved: fresh-path index ordering + framing

Round-4 caught the inverted risk in the fresh path (`write_current_index`
precedes the `activate_build` CAS — a CAS loss strands the index on a
phantom version). Both paths now write the index only after a successful
activation commit, inside the lock. Problem framing corrected to
acknowledge the existing completed-gated strategy endpoint (the gap is
no-strategy-change + versioned republish, not "no client path at all").

### 2026-07-10 (r3) — Cold-critic BLOCKER resolved: `_activate_existing` stale current.json

Round-3 verified `_activate_existing` never calls `write_current_index` —
the idempotent path this ticket relies on leaves the on-disk index stale
until a lazy read. Resolution: mitigation (a) adopted — the call is added
inside `_activate_existing`, with an AC asserting `current.json` is
correct immediately after the 200. Lock scope pinned to the whole
`build_and_activate` critical section (INFO finding), and the lock itself
is now consumed from AE-0316 (new blocked-by) so AE-0311 and this ticket
share one implementation.

### 2026-07-10 (r2) — Cold-critic findings resolved: shared lock domain + first-time-finalize edge

Round-2: the build advisory lock is declared as the shared serialization
domain with AE-0311's repair (repair acquires it too). Added a regression
AC for first-time finalize with a stale `artifact_version` from a prior
partial run, since the health-check fix changes the path every finalize
validates against.

### 2026-07-10 — Cold-critic WARN resolved: build serialization is net-new

External GLM 5.2 review verified no lock/CAS exists around
`build_and_activate` — the "existing CAS/lock semantics" wording was wrong.
Resolution: per-project advisory lock (or `building` CAS on
`carousel_artifact_builds`) added to scope with a concurrency AC +
Gherkin; the `completed`↔`phase_status` invariant must be pinned by test
so republish and resume can never mutate the same project concurrently.

## Blockers

None.

## Final Summary

Pending.
