# Editorial Workflow Resume Gap — Plan

> Status: Superseded — historical record

**Status:** Accepted
**Date:** 2026-05-24
**Last validated:** 2026-05-28
**Traceability:** ADR-0007, `docs/plans/carousel-pipeline-consolidation.md` §4.3, CP-004, CP-006
**Scope:** Fix resume transport failures, artifact hydration without refresh, and async resume per ADR-0007.

---

## 1. Problem Statement

Three distinct failures remain after polling recovery shipped:

| Layer | Symptom | Current mitigation |
|-------|---------|-------------------|
| **Transport** | Next.js proxy / socket hang up on 90s+ `POST /workflow/resume` | Polling recovery hides false error banner |
| **Data freshness** | `awaiting_human` reached before artifacts land → empty review panel until refresh | Manual refresh |
| **Architecture** | Resume handler awaits full graph continuation (43–102s+ LLM work) | Violates ADR-0007 p95 < 2s |

Background tasks are **not** required for Phase 1 (artifact hydration + transport hardening). They **are** required for Phase 2 (ADR compliance) and before image-generation E2E.

---

## 2. Phased Approach

### Phase 1 — Artifact hydration + transport hardening (no background tasks)

**Goal:** E2E passes research → outline → content without refresh or error banner, even when resume HTTP fails.

| Task ID | Work |
|---------|------|
| RW-001 | Route resume to backend directly in dev; verify nginx 300s in prod |
| RW-002 | Poll until **artifacts present**, not only gate status |
| RW-003 | Merge `artifact` SSE events into UI during recovery |
| RW-004 | Keep `loading` until phase-specific artifacts visible |

**Exit criteria:** Playwright E2E `@cp-resume-gap` scenarios green without manual refresh.

### Phase 2 — Async resume (background execution)

**Goal:** `POST /workflow/resume` returns 202 in < 2s; generation continues via background task + SSE.

| Task ID | Work |
|---------|------|
| RW-010 | Return 202 Accepted immediately after validate + persist |
| RW-011 | Schedule `resume_workflow()` via `asyncio.create_task` + fresh DB session |
| RW-012 | Concurrency guard: reject resume while `in_progress` (409) |
| RW-013 | SSE terminal events: `review_required`, `artifact`, `error` |
| RW-014 | Frontend treats 202 as success; simplify transport-failure polling |

**Exit criteria:** Backend scenario "Approve research returns within 2 seconds" passes; image phase E2E completes.

### Phase 3 — Production hardening (optional)

Only when running multiple backend replicas:

| Task ID | Work |
|---------|------|
| RW-020 | Redis pub/sub for workflow SSE hub |
| RW-021 | Durable job queue (Redis Streams / ARQ) with retries |

---

## 3. Gherkin Scenarios

Gherkin-first per project standards. Add scenarios to existing feature files; do not create orphan tests.

### 3.1 Feature file targets

| File | New tags |
|------|----------|
| `backend/tests/features/carousel_pipeline_consolidation.feature` | `@cp-resume-gap @cp-async-resume` |
| `frontend/tests/features/carousel_editorial_consolidation.feature` | `@cp-resume-gap @cp-async-resume` |

### 3.2 Phase 1 — Transport recovery & artifact hydration

#### Backend (`@cp-resume-gap`)

```gherkin
@cp-consolidation @cp-resume-gap
Feature: Resume transport resilience and artifact readiness
  As the editorial workflow API
  I want resume to be decoupled from artifact availability checks
  So that clients can recover when HTTP transport fails but generation succeeds

  Background:
    Given I am authenticated as an editor
    And a carousel project exists with attached source materials

  @cp-edge @cp-resume-gap
  Scenario: Workflow state includes outline artifacts when outline gate opens
    Given the workflow is awaiting human review at phase "outline"
    When I send a GET request to "/api/carousels/{project_id}/workflow/state"
    Then the workflow state outline should not be empty
    And the workflow state phase_status should be "awaiting_human"

  @cp-edge @cp-resume-gap
  Scenario: Workflow state includes slide drafts when content gate opens
    Given the workflow is awaiting human review at phase "content"
    When I send a GET request to "/api/carousels/{project_id}/workflow/state"
    Then the workflow state slide_drafts should not be empty
    And the workflow state slide_drafts count should be at least the outline slide count

  @cp-happy-path @cp-resume-gap @cp-sse-primary
  Scenario: Artifact SSE event published when outline generation completes
    Given a client is subscribed to "/api/carousels/{project_id}/workflow/stream"
    And the workflow phase_status is "in_progress" at phase "outline"
    When outline generation completes
    Then the client should receive an "artifact" SSE event with artifact_type "outline"
    And the artifact payload outline should not be empty

  @cp-happy-path @cp-resume-gap @cp-sse-primary
  Scenario: Artifact SSE event published when content drafts complete
    Given a client is subscribed to "/api/carousels/{project_id}/workflow/stream"
    And the workflow phase_status is "in_progress" at phase "content"
    When content generation completes
    Then the client should receive an "artifact" SSE event with artifact_type "slide_drafts"
    And the artifact payload slide_drafts should not be empty
```

#### Frontend (`@cp-resume-gap`)

```gherkin
@cp-consolidation @cp-resume-gap
Feature: Resume recovery without false errors or manual refresh
  As an editor
  I want approvals to show artifacts automatically
  So that I can review without refreshing when resume transport fails

  Background:
    Given I am logged in as an editor
    And I open the create workspace for carousel project "{project_id}"

  @cp-edge @cp-resume-gap
  Scenario: Resume transport failure does not show error banner when workflow recovers
    Given the editorial workflow is awaiting human review at phase "research"
    And the next POST "/api/carousels/{project_id}/workflow/resume" will fail with status 500 or network error
    When I click "Approve Phase"
    And the workflow eventually reaches phase "outline" with phase_status "awaiting_human"
    Then I should not see an error banner about resuming the workflow
    And the approve action should remain in a loading state until recovery completes or fails definitively

  @cp-happy-path @cp-resume-gap
  Scenario: Outline artifacts appear without manual page refresh after research approval
    Given the editorial workflow is awaiting human review at phase "research"
    When I click "Approve Phase"
    And the workflow reaches phase "outline" with phase_status "awaiting_human"
    Then I should see outline slides in the review panel
    And I should not need to reload the page

  @cp-happy-path @cp-resume-gap
  Scenario: Content slide drafts appear without manual page refresh after outline approval
    Given the editorial workflow is awaiting human review at phase "outline"
    When I click "Approve Phase"
    And the workflow reaches phase "content" with phase_status "awaiting_human"
    Then I should see slide drafts in the review panel
    And I should not need to reload the page

  @cp-edge @cp-resume-gap
  Scenario: Loading state persists until expected artifacts exist for the next gate
    Given the editorial workflow is awaiting human review at phase "research"
    When I click "Approve Phase"
    And the workflow phase_status becomes "awaiting_human" at phase "outline"
    But outline artifacts are not yet present in client state
    Then the approve action should remain loading
    When outline artifacts become available via SSE or state hydration
    Then the approve action should stop loading
    And I should see outline slides in the review panel

  @cp-happy-path @cp-resume-gap @cp-sse-primary
  Scenario: Artifact SSE hydrates review panel during resume recovery
    Given the create workspace has an active workflow SSE subscription
    And the editorial workflow is awaiting human review at phase "research"
    When I click "Approve Phase"
    And an "artifact" SSE event arrives with artifact_type "outline"
    Then the outline review panel should update without a full page reload
    And the browser should not require manual refresh to show outline slides

  @cp-edge @cp-resume-gap @cp-sse-fallback
  Scenario: Polling recovery waits for artifacts not only gate status
    Given the create workspace has an active workflow SSE subscription
    And the editorial workflow is awaiting human review at phase "outline"
    When I click "Approve Phase"
    And POST "/api/carousels/{project_id}/workflow/resume" fails with a transport error
    And GET "/api/carousels/{project_id}/workflow/state" returns phase "content" and phase_status "awaiting_human"
    But slide_drafts are still empty
    Then the client should continue recovery polling
    When slide_drafts become non-empty in workflow state
    Then recovery polling should stop
    And I should see slide drafts in the review panel
```

### 3.3 Phase 2 — Async resume (`@cp-async-resume`)

#### Backend

```gherkin
@cp-consolidation @cp-async-resume
Feature: Async editorial workflow resume
  As the editorial workflow API
  I want resume to return immediately and run generation in the background
  So that HTTP clients and proxies never block on LLM work

  Background:
    Given I am authenticated as an editor
    And a carousel project exists with attached source materials

  @cp-happy-path @cp-async-resume
  Scenario: Approve research returns 202 within 2 seconds
    Given the workflow is awaiting human review at phase "research"
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action  | approve |
    Then the response status should be 202
    And the response should return within 2 seconds
    And the response body phase_status should be "in_progress"
    And the workflow eventually reaches phase "outline" with phase_status "awaiting_human"

  @cp-happy-path @cp-async-resume @cp-sse-primary
  Scenario: Background resume publishes review_required when outline gate opens
    Given a client is subscribed to "/api/carousels/{project_id}/workflow/stream"
    And the workflow is awaiting human review at phase "research"
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action  | approve |
    Then the response status should be 202
    And the client should receive a "review_required" SSE event for phase "outline"
    And the review_required payload outline should not be empty

  @cp-edge @cp-async-resume
  Scenario: Resume while phase_status is in_progress returns 409
    Given the workflow phase_status is "in_progress" at phase "outline"
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action  | approve |
    Then the response status should be 409
    And the response detail should indicate resume already in progress

  @cp-edge @cp-async-resume @cp-lock
  Scenario: Duplicate approve with same expected_version is idempotent
    Given the workflow is awaiting human review at phase "research"
    And the workflow expected_version is 4
    When I send two POST requests to "/api/carousels/{project_id}/workflow/resume" with body:
      | action           | approve |
      | expected_version | 4       |
    Then one response should have status 202
    And the other response should have status 202 or 409
    And the workflow should advance to outline exactly once

  @cp-edge @cp-async-resume
  Scenario: Background resume failure publishes recoverable error event
    Given the workflow is awaiting human review at phase "outline"
    And outline generation will fail in the background worker
    When I send a POST request to "/api/carousels/{project_id}/workflow/resume" with body:
      | action  | approve |
    Then the response status should be 202
    And a client subscribed to "/api/carousels/{project_id}/workflow/stream" should receive an "error" SSE event with recoverable true
    And the workflow state phase_status should eventually be "failed"

  @cp-edge @cp-async-resume @cp-recovery
  Scenario: Server restart during background resume resumes from checkpoint
    Given the workflow phase_status is "in_progress" at phase "content"
    When the application restarts before content generation completes
    And I send a GET request to "/api/carousels/{project_id}/workflow/state"
    Then the workflow state should not be stuck in an unrecoverable state
    And the workflow should eventually reach "awaiting_human" or "failed" with an audit entry
```

#### Frontend

```gherkin
@cp-consolidation @cp-async-resume
Feature: Async resume client behavior
  As an editor
  I want immediate feedback on approve without waiting for generation
  So that the UI stays responsive during long phases

  @cp-happy-path @cp-async-resume @cp-sse-primary
  Scenario: Approve clears loading via SSE not resume HTTP response
    Given the editorial workflow is awaiting human review at phase "research"
    And the create workspace has an active workflow SSE subscription
    When I click "Approve Phase"
    And POST "/api/carousels/{project_id}/workflow/resume" returns 202 within 2 seconds
    Then the browser should not poll "/api/carousels/{project_id}/workflow/state" on an interval while SSE is healthy
    And the next gate should open when a "review_required" SSE event arrives

  @cp-edge @cp-async-resume
  Scenario: Double-click approve does not enqueue duplicate background jobs
    Given the editorial workflow is awaiting human review at phase "outline"
    When I double-click "Approve Phase" rapidly
    Then at most one POST "/api/carousels/{project_id}/workflow/resume" should succeed with 202
    And I should not see duplicate phase transitions in the workflow state

  @cp-edge @cp-async-resume @cp-sse-fallback
  Scenario: SSE disconnect during background resume uses polling fallback until gate opens
    Given the editorial workflow is awaiting human review at phase "images"
    And POST "/api/carousels/{project_id}/workflow/resume" returns 202
    When the SSE connection fails during image generation
    Then the client should enter polling-fallback mode
    And polling should stop when phase_status becomes "awaiting_human" and image_assets are non-empty
```

### 3.4 Phase 3 — Multi-worker (`@cp-async-resume @cp-scale`)

```gherkin
@cp-edge @cp-async-resume @cp-scale
Scenario: SSE subscriber on worker B receives events published by worker A
  Given two backend replicas are running
  And a client is subscribed to "/api/carousels/{project_id}/workflow/stream" on replica B
  When a background resume job runs on replica A and publishes progress
  Then the client on replica B should receive the same progress payload
```

---

## 4. Edge Cases

| ID | Edge case | Phase | Expected behavior |
|----|-----------|-------|-------------------|
| EC-01 | Resume HTTP 500/502/504 but backend succeeds | 1 | No error banner; recovery until artifacts present |
| EC-02 | Gate status `awaiting_human` before artifacts written | 1 | Continue recovery; keep loading until artifacts |
| EC-03 | SSE delivers `phase_change` before `artifact` | 1 | UI waits for artifact event or state poll with artifact check |
| EC-04 | SSE disconnected during long resume | 1, 2 | Polling fallback with artifact-aware stop condition |
| EC-05 | User refreshes mid-recovery | 1, 2 | Mount hydrate restores `phase_progress` + artifacts from state |
| EC-06 | Double-click Approve | 2 | Second request 409 or idempotent 202; single graph advance |
| EC-07 | Resume while `in_progress` | 2 | 409 with clear message; no parallel graph runs |
| EC-08 | Optimistic lock mismatch during approve | 2 | 409; UI refreshes state and shows conflict message |
| EC-09 | Background job raises after 202 returned | 2 | SSE `error` + `phase_status: failed`; audit log entry |
| EC-10 | Process killed mid-background-job | 2 | On restart, state reflects checkpoint; admin alert if stuck > N min |
| EC-11 | Image phase exceeds any proxy timeout (5–15 min) | 2 | 202 + SSE progress; no blocking HTTP |
| EC-12 | Client treats 200 as success during migration | 2 | Backend may accept both 200/202 temporarily; frontend prefers 202 |
| EC-13 | Polling stops at `awaiting_human` but `slide_drafts` empty | 1 | **Bug today** — fixed by artifact-aware poll stop (EC-02) |
| EC-14 | Next.js dev proxy socket hang up persists | 1 | Direct backend resume URL env flag for dev; prod nginx bypasses Next |
| EC-15 | Rate limit during fallback polling burst | 1 | Workflow state reads exempt from public rate limit (existing `@cp-sse-rate-limit`) |
| EC-16 | Multi-tab same project approve | 2 | Optimistic lock on second tab → 409 |
| EC-17 | Revise action during background approve | 2 | 409 while `in_progress`; revise allowed only at `awaiting_human` |
| EC-18 | SSE hub in-process; resume on different worker | 3 | Redis pub/sub required; document as known limitation until RW-020 |

---

## 5. Risks and Mitigations

| Risk | Severity | Phase | Mitigation |
|------|----------|-------|------------|
| **False sense of completion** — polling stops at gate status without artifacts | High | 1 | RW-002 artifact-aware recovery; Gherkin EC-02, EC-13 |
| **Transport timeout masks backend success** | High | 1 | No error banner on transport failure; poll/SSE until artifacts or definitive failure |
| **Blocking resume breaks image E2E** | High | 2 | RW-010–014 async resume before image phase testing |
| **Duplicate background jobs** — double approve | High | 2 | RW-012 in_progress guard; idempotency key on `(project_id, expected_version, action)` |
| **Stuck `in_progress`** after worker crash | High | 2 | Startup sweeper marks stale jobs failed after timeout; workflow alert worker (Phase 5) |
| **Lost SSE events** during disconnect | Medium | 1, 2 | Persist `phase_progress` + artifacts on project row; hydrate on reconnect |
| **Race: SSE artifact before state DB commit** | Medium | 1 | SSE payload includes artifact snapshot; client merges optimistically |
| **Frontend complexity** — two recovery paths (transport + artifact) | Medium | 1 | Shared `pollUntilWorkflowReady()` util with phase-specific artifact predicates |
| **`asyncio.create_task` lost on shutdown** | Medium | 2 | Graceful shutdown hook awaits in-flight tasks or marks failed; Phase 3 queue |
| **Single-worker BackgroundTasks limitation** | Low | 2 | Document in ADR; acceptable for Docker dev/staging |
| **Multi-worker SSE gap** | High (prod) | 3 | RW-020 Redis pub/sub before horizontal scaling |
| **Integration test churn** — 200 → 202 | Low | 2 | Update backend tests; keep temporary 200 shim behind feature flag if needed |
| **Polling load under many editors** | Low | 1, 2 | Backoff caps; stop at gate+artifacts; SSE primary per ADR-0007 |
| **User clicks approve on stale artifacts** | Medium | 2 | `expected_version` required on resume; 409 refreshes UI |

---

## 6. Task Acceptance Criteria

### RW-001 — Transport routing

- [x] Dev: `NEXT_PUBLIC_API_URL` routes workflow resume/state/stream directly to backend `:8000` via `resolveClientApiUrl()`
- [x] Prod: nginx `proxy_read_timeout 300s` verified for `/workflow/resume`
- [x] `# Scenario: Resume transport failure does not show error banner…` passes

### RW-002 — Artifact-aware polling

- [x] `pollUntilWorkflowReady()` (internal) uses artifact predicates via `isWorkflowReady()`
- [x] Outline gate: `outline.length > 0`
- [x] Content gate: `slide_drafts.length >= outline.length` (or > 0 minimum)
- [x] `# Scenario: Polling recovery waits for artifacts not only gate status` passes

### RW-003 — SSE artifact hydration

- [x] Hook merges `artifact` events into `state.outline`, `state.slide_drafts`, etc.
- [x] `# Scenario: Artifact SSE hydrates review panel during resume recovery` passes

### RW-004 — Loading until artifacts visible

- [x] `loading` clears only when artifact predicate satisfied or `phase_status === failed`
- [x] `# Scenario: Loading state persists until expected artifacts exist…` passes (Vitest)

### RW-010 — 202 Accepted contract

- [x] `POST /workflow/resume` returns 202 + `{ accepted: true, phase_status: in_progress, lock_version }`
- [x] p95 < 2s measured in integration test
- [x] `# Scenario: Approve research returns 202 within 2 seconds` passes

### RW-011 — Background execution

- [x] `resume_workflow()` runs in background with fresh DB session
- [x] Langfuse trace linked to same `project_id`
- [x] `# Scenario: Background resume publishes review_required…` passes

### RW-012 — Concurrency guard

- [x] Second resume while `in_progress` → 409
- [x] `# Scenario: Resume while phase_status is in_progress returns 409` passes

### RW-013 — SSE terminal events

- [x] Background completion emits `review_required` with full interrupt payload
- [x] Failure emits `error` with `recoverable: true|false` (client-safe allowlisted messages)

### RW-014 — Frontend async client

- [x] Treat 202 as success; SSE-first wait with polling fallback when SSE unhealthy
- [x] `# Scenario: Approve clears loading via SSE not resume HTTP response` passes

---

## 7. Traceability Matrix

| Task | Gherkin scenarios | Edge cases | Risks mitigated |
|------|-------------------|------------|-----------------|
| RW-001 | Resume transport failure does not show error banner | EC-01, EC-14 | Transport timeout masks success |
| RW-002 | Polling recovery waits for artifacts… | EC-02, EC-13 | False sense of completion |
| RW-003 | Artifact SSE hydrates review panel… | EC-03 | Race SSE vs state |
| RW-004 | Loading state persists until artifacts… | EC-02 | Empty review flash |
| RW-010 | Approve research returns 202 within 2 seconds | EC-11, EC-12 | Blocking resume / image E2E |
| RW-011 | Background resume publishes review_required… | EC-10 | Stuck in_progress |
| RW-012 | Resume while in_progress returns 409; Double-click approve | EC-06, EC-07, EC-16 | Duplicate jobs |
| RW-013 | Background resume failure publishes error… | EC-09 | Stuck in_progress |
| RW-014 | Approve clears loading via SSE… | EC-04, EC-05 | Lost SSE events |
| RW-020 | SSE subscriber on worker B… | EC-18 | Multi-worker SSE gap |

---

## 8. Test Implementation

| Scenario domain | Backend tests | Frontend tests |
|-----------------|---------------|----------------|
| Artifact readiness | `tests/integration/test_carousel_pipeline_consolidation.py` | Vitest `use-editorial-workflow.test.ts` |
| Transport recovery | — | Vitest + Playwright `@cp-resume-gap` |
| Async resume | `tests/integration/test_carousel_pipeline_consolidation.py` | Vitest + Playwright `@cp-async-resume` |
| E2E happy path | — | `frontend/tests/e2e/carousel-editorial-gherkin.spec.ts` |

Run isolation:

```bash
# Backend
cd backend && uv run pytest tests/integration/test_carousel_pipeline_consolidation.py -k "resume_gap or async_resume" -v

# Frontend
cd frontend && npm run test -- --run src/features/create/hooks/use-editorial-workflow.test.ts
cd frontend && npm run test:e2e -- --grep "@cp-resume-gap"
```

---

## 9. Decision Summary

| Question | Answer |
|----------|--------|
| Are background tasks necessary **now**? | No for Phase 1; yes before image E2E and ADR compliance |
| Minimum shippable increment | Phase 1 (RW-001–004) |
| Target architecture | Phase 2 (RW-010–014) per ADR-0007 |
| Phase 3 timing | Only when scaling beyond single backend worker |
