# AE-0426 — Rebuild hidden bad posts as drafts via the new pipeline (E)

Status: Dev Complete
Tier: T2
Priority: P2
Type: Feature
Area: Cross-cutting
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: feat/ae-0426-rebuild-hidden-posts
Kanban Card: TBD
Created: 2026-10-18
Updated: 2026-10-19

## Goal

Take the carousel-origin posts hidden under AE-0422's selection criteria and rebuild them as drafts
through the new writer pipeline (AE-0425), so the owner reviews each and republishes. This is the
one-off recovery of every already-published old-pipeline row.

## Problem

Every already-published carousel-origin post (10 at cutover) was assembled by the old pipeline:
carousel-slide images injected at read time, baked-in text, no owner voice. They were all hidden
(status → draft) by the orchestrator with owner approval — there is no body-length/H1 filter. They
must be regenerated as v2 drafts with the owner's voice and generated images, then reviewed.

## Scope

- A one-off operational script (`scripts/blog/rebuild_hidden_posts.py`) that selects rows by the
  **durable hide marker** written by AE-0422
  (`ai_generation_metadata.hidden_bad_post` present and `rebuilt_at` absent), independent of the
  current `status` (hiding sets `draft`; a status-based selector would immediately go empty). For
  each row it composes inputs from its carousel (research findings, outline,
  `long_form_notes`), calls the writer pipeline (AE-0425) to produce a **draft** v2 document with
  cover + section images, and leaves `status = "draft"` for owner review.
- Idempotent and resumable: after a successful rebuild, set
  `hidden_bad_post.rebuilt_at = now` (keep the marker for audit) and skip rows with `rebuilt_at`
  set; also skip rows already at `schema == "blog.v2"` with a stored quality score. A re-run never
  creates a second row per project.
- A dry-run mode listing the target rows and the marker that selected each (origin+status was the
  prod sweep; there is no content-quality filter to report).

## Non-Goals

- Auto-publishing any rebuilt post (owner reviews and publishes).
- The writer itself (AE-0425) and the cutover (AE-0423).
- Rows whose carousel no longer exists (report and skip).

## Acceptance Criteria

- [x] AC1: The script selects exactly the rows carrying AE-0422's hide marker with no
      `rebuilt_at`, and lists them in `--dry-run`. (store `candidates()`, `preview()`,
      `test_marker_selection_ignores_status`, `test_dry_run_selects_only_marked_rows`)
- [x] AC2: For each target row, a single v2 draft is produced with a cover, one image per section,
      and stored `content.quality.voice_score` + `translations.en.quality`.
      (`test_rebuild_produces_a_v2_draft_with_images`)
- [x] AC3: No target row ends `status == "published"`; all remain `draft`.
      (`test_rebuild_never_publishes`, every apply test asserts `status == draft`)
- [x] AC4: Re-running the script is a no-op for already-rebuilt rows (`rebuilt_at` set; idempotent)
      and never creates a duplicate `blog_posts` row per project.
      (`test_second_run_is_a_noop_and_creates_no_duplicate`)
- [x] AC5: Rows whose carousel is missing are reported and skipped without error.
      (`test_missing_carousel_is_skipped_without_error`)
- [x] AC6: The run is observable: a summary (selected / rebuilt / skipped / failed) and Langfuse
      traces per post. (`format_report()`, CLI `init_langfuse`, pipeline `blog_phase_trace`)

## Gherkin Scenarios

- `backend/tests/features/blog_rebuild_hidden_ae0426.feature`.
- Scenario list: dry-run lists all marker-selected targets (including rows already at `draft`, and
  rows the old body-length/H1 filter would have missed); rebuild produces a draft with images and
  PT/EN scores; `rebuilt_at` makes the re-run a no-op; missing carousel skipped; never publishes; a
  plain draft without the marker is not selected.

## Delta

### ADDED

- `backend/src/rag_backend/scripts/rebuild_hidden_posts.py` — packaged CLI (`--apply`, summary).
- `scripts/blog/rebuild_hidden_posts.py` — thin shim at the ticket-literal path (delegates; the
  deploy image only copies `backend/src`).
- `backend/src/rag_backend/application/services/blog/blog_rebuild.py` — selection, CAS start,
  generation, stamping, report.
- `backend/src/rag_backend/infrastructure/database/blog_rebuild_store.py` — SQL rebuild store.
- `backend/src/rag_backend/infrastructure/database/blog_rebuild_materials.py` — carousel/persona/
  workflow-state material source.
- `backend/src/rag_backend/bootstrap/blog_rebuild.py` — composition root.
- `backend/src/rag_backend/domain/constants/blog_rebuild.py` — marker keys, criteria, outcomes, logs.
- Five test modules (4 unit + 1 integration) and the feature spec above.

### MODIFIED

- `backend/src/rag_backend/infrastructure/database/blog_post_hide.py` — import the shared marker
  constant (no behavior change).

### REMOVED

- None.

## Affected Areas

- Backend: operational script
- Frontend: none
- Database: rewrites `content` of hidden rows (no schema change)
- API: none (calls the service layer)
- Tests: script unit + feature
- Docs: this ticket + a short runbook note
- Prompts/LLM: uses `blog/v1` prompts
- Observability: per-post Langfuse trace + run summary
- Deployment: run once after D ships; **not** a deploy step

## Dependencies

- Blocks: none.
- Blocked by: AE-0425 (writer + images), AE-0423 (document shape).
- Related: AE-0422 (selection criteria), QA F-04/F-05.

## Implementation Plan

1. Feature spec + script skeleton with `--dry-run`.
2. Reuse the AE-0425 generation service; select rows by the AE-0422 **durable marker**, not by
   `status = "published"` (hiding already changed the status).
3. Idempotency guard + summary output.
4. Unit + feature tests.

## QA Checklist

- [ ] Security reviewed (no secrets, no destructive delete)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (missing carousel, partial images, re-run)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-18 16:30

Ticket created from the AE-0422 plan (ADR-0025, wave E).

### 2026-10-19

Rebased onto the new AE-0425 tip (AE-0424 slot-write path). `start_attempt` now resets the legacy
body to a fresh `blog.v2` document (the slot path refuses non-v2 rows), the generation factory takes
the row author (or the audit actor) so slot writes and the trace share one identity, and the job
sets `retitle=True` so the draft takes the writer's title.

Standalone-process hardening from the AE-0422 prod run: imports of settings/DB/checkpointer/bootstrap
are lazy so `--help` needs no settings; `--dry-run` is explicit (still the default); every structlog
call is key/value (no `%` formatting). A real-subprocess test runs `--help` with settings removed and
`--dry-run` against a file SQLite DB. Runbook uses
`docker compose exec backend python -m rag_backend.scripts.rebuild_hidden_posts`.

### 2026-10-19

Implemented on branch `feat/ae-0426-rebuild-hidden-posts` (rebased onto
`feat/ae-0425-blog-writer-voice-images`). Initial full backend gate run was green (22/22, mutation
79.10%). Addressed orchestrator code review: operator guard rails (`--only`, `--limit`,
`--max-posts`), published-row protection, missing-notes skips, dry-run material checks, whole-post
error isolation, non-zero exit and Langfuse flush. Reviewer fixes: non-DB backend gates green,
focused tests 48 passed; DB/mutation gates deferred to CI (Docker daemon unavailable locally; worker
rule forbids local mutation).

### 2026-10-19 (final)

Rebased onto the current base tip `3cdcec038` (the previous tip `7510a2670` carried a stray
`f90105f3bcf2__driftcheck` migration that broke Strict Diff and six migration-head tests;
`3cdcec038` drops it). Adapted the integration harness to the latest slot-write wiring
(`SlotWriteGenerationStore(..., RunOwner(user_id=..., image_cap=...))`, `image_cap` moved out of
`BlogGenerationDeps`). `7f9b3c5fa`: CI fully green — Test & Coverage 16m57s, Mutation 33m31s,
Strict Diff pass, backend-gate pass, merge state CLEAN. The next base tip added aiohttp advisories,
so the branch was rebased onto `e2410af45` (aiohttp 3.14.5) and `pip-audit` is clean locally.

## Files Touched

- `backend/src/rag_backend/domain/constants/blog_rebuild.py` — new constants (marker keys, criteria,
  outcomes, log events).
- `backend/src/rag_backend/application/services/blog/blog_rebuild.py` — rebuild service + protocols.
- `backend/src/rag_backend/application/services/blog/blog_rebuild_selection.py` — selection
  predicate, report/selection types and operator caps.
- `backend/src/rag_backend/infrastructure/database/blog_rebuild_store.py` — SQL candidate selection,
  CAS `start_attempt` (published guard), `mark_rebuilt`.
- `backend/src/rag_backend/infrastructure/database/blog_rebuild_materials.py` — material loading
  (project, slides, persona, workflow state).
- `backend/src/rag_backend/infrastructure/database/blog_post_hide.py` — shared marker constant.
- `backend/src/rag_backend/bootstrap/blog_rebuild.py` — service wiring.
- `backend/src/rag_backend/scripts/rebuild_hidden_posts.py` — packaged CLI.
- `scripts/blog/rebuild_hidden_posts.py` — ticket-literal shim.
- `backend/tests/unit/application/test_blog_rebuild_ae0426.py`
- `backend/tests/unit/infrastructure/test_blog_rebuild_store_ae0426.py`
- `backend/tests/unit/infrastructure/test_blog_rebuild_materials_ae0426.py`
- `backend/tests/unit/scripts/test_rebuild_hidden_posts_ae0426.py`
- `backend/tests/integration/test_blog_rebuild_hidden_ae0426.py`
- `docs/architecture/blog-post-document-model.md` — operator runbook note.

## Test Evidence

Final tree (base tips through `e2410af45`; non-DB gates run individually):

```
GATES_JSON: {"pass":17,"fail":0,"skip":0,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:autopilot-env","status":"PASS"},{"gate":"backend:healthcheck-loopback","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"}]}
```

DB/mutation gates deferred to CI. CI evidence: `7f9b3c5fa` had every substantive check green
(Test 16m57s, Mutation 33m31s); `177df5495` failed `backend-gate` only on the new `aiohttp 3.14.3`
`pip-audit` advisories, fixed by rebasing onto `e2410af45` (aiohttp 3.14.5).

Earlier full run (before the review fixes):

```
GATES_JSON: {"pass":22,"fail":0,"skip":0,"results":[{"gate":"backend:format","status":"PASS"},{"gate":"backend:lint","status":"PASS"},{"gate":"backend:lint-diff","status":"PASS"},{"gate":"backend:blanket-ignore","status":"PASS"},{"gate":"backend:strict-diff","status":"PASS"},{"gate":"backend:type","status":"PASS"},{"gate":"backend:imports","status":"PASS"},{"gate":"backend:arch-ratchet","status":"PASS"},{"gate":"backend:docstrings","status":"PASS"},{"gate":"backend:dead-code","status":"PASS"},{"gate":"backend:inline-prompts","status":"PASS"},{"gate":"backend:redis-factory","status":"PASS"},{"gate":"backend:autopilot-env","status":"PASS"},{"gate":"backend:healthcheck-loopback","status":"PASS"},{"gate":"backend:bandit","status":"PASS"},{"gate":"backend:pip-audit","status":"PASS"},{"gate":"backend:integrity","status":"PASS"},{"gate":"backend:test","status":"PASS"},{"gate":"backend:diff-cover","status":"PASS"},{"gate":"backend:migrations","status":"PASS"},{"gate":"backend:schema-drift","status":"PASS"},{"gate":"backend:mutation","status":"PASS"}]}
```

- Non-DB backend gates (format, lint, lint-diff, blanket-ignore, strict-diff, type, imports,
  arch-ratchet, docstrings, dead-code, inline-prompts, redis-factory, autopilot-env,
  healthcheck-loopback, bandit, pip-audit, integrity): 17/17 PASS.
- DB-dependent gates (`test`, `diff-cover`, `migrations`, `schema-drift`): deferred to CI (the local
  Docker daemon is unavailable after the machine restart, so there is no Postgres).
- `mutation`: deferred to CI — the worker rule forbids running mutmut locally (machine OOM).
- Focused AE-0426 + hide tests: 48 passed.
- Earlier full run (before the review fixes): 22/22 PASS, mutation 79.10% (threshold 75%).
- `scripts/ci/check-integrity.sh backend`: no net-new gaming (0 blockers, 0 warnings).

## QA Report

Pending.

## Decision Log

- **Drafts, not republished.** The owner must review the new voice/images before anything goes live
  (owner decision 3).
- **Idempotent by project.** A re-run must not create a second blog row for the same carousel.
  The rebuild reuses the existing row (CAS on `lock_version`) rather than inserting.
- **Selection is marker-based, not status-based.** Hiding already set `status = draft`; the selector
  keys on `ai_generation_metadata.hidden_bad_post` present + `rebuilt_at` absent.
- **`partial` image outcome counts as rebuilt.** It stamps `rebuilt_at` (the draft is reviewable);
  only `failed` (or a lost lease) leaves it unset so the next run retries.
- **Packaged CLI + root shim.** The deploy image copies only `backend/src`, so the logic lives in
  `rag_backend/scripts/rebuild_hidden_posts.py`; `scripts/blog/rebuild_hidden_posts.py` delegates for
  the ticket-literal path (operators run it from a checkout).
- **Marker is kept after rebuild** (`rebuilt_at` nested under it) for audit/history.
- **Operator guard rails.** `--only` narrows to post ids, `--limit` narrows the selection list,
  `--max-posts` is an apply-only spend cap defaulting to 1 (run one post first), and the dry run is
  never truncated by it. Omitted rows are counted in the summary.
- **Published rows are protected.** They are skipped as `currently_published` unless
  `--include-published` is explicit; the SQL `start_attempt` also refuses a published row unless
  allowed, so a publish racing the selection cannot be silently undone.
- **Missing `long_form_notes` is a skip.** A carousel with no notes would produce an ungrounded,
  paid generation; the dry run and the run both report `missing_notes` before any LLM call.
- **Whole-post error isolation.** Material load, generation and the stamp write are all inside the
  per-post try; the summary is printed in `finally` and a failed post exits non-zero.
- **Run inside the prod backend container**, not a checkout: images are written to the
  `carousel_output_dir/blog-images` volume, and Langfuse is flushed before exit.

## Risk & Size

- **Risk:** Low — one-off operator script; mitigated by --dry-run, idempotency and never publishing.
- **Size:** S

## Blockers

None.

## Final Summary

One-off, idempotent rebuild of the AE-0422-hidden posts through the AE-0425 writer pipeline. Dry-run
by default; `--apply` rewrites the existing row into a `blog.v2` draft with images and voice scores,
never publishes, and stamps `hidden_bad_post.rebuilt_at` so re-runs are no-ops. Operators start with
`--only <id>`; `--max-posts` defaults to 1 as a spend cap. Missing carousels/notes and published rows
are reported and skipped (published only with `--include-published`); per-post failures do not abort
the run, the summary always prints, and a failed post exits non-zero.
