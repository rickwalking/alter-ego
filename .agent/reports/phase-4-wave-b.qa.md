# QA Validation Report — Phase 4 Wave B

**Branch:** `feat/phase-4-editorial-carousel` vs `origin/main`
**Wave:** AE-0107 + AE-0109
**Mode:** wave (external, read-only)
**Iteration:** 1

---

## Overall Verdict: FAIL

Mutation gate is below threshold (62.30% < 75%). Per verdict policy, any gate FAIL ⇒ overall FAIL.

---

## Gate Reproduction (`scripts/ci/gates.sh backend`)

| Gate | Status | Notes |
|------|--------|-------|
| backend:format | PASS | |
| backend:lint | PASS | |
| backend:lint-diff | PASS | |
| backend:blanket-ignore | PASS | |
| backend:strict-diff | PASS | |
| backend:type | PASS | |
| backend:imports | PASS | 14 kept / 0 broken |
| backend:arch-ratchet | PASS | `import_baseline.py --check` PASS (62≤63 runtime pairs) |
| backend:docstrings | PASS | 82.4% ≥ 80% |
| backend:dead-code | PASS | |
| backend:bandit | PASS | |
| backend:pip-audit | PASS | |
| backend:integrity | PASS | 0 net-new blockers |
| backend:test | SKIP | No Postgres locally — CI decides |
| backend:diff-cover | SKIP | No Postgres locally — CI decides |
| backend:migrations | SKIP | No Postgres locally — CI decides |
| backend:mutation | **FAIL** | **62.30% < 75%** (1560 killed, 400 survived, 4 timeout, 1 no_tests / 1965 total) |

**GATES_JSON:** `{"pass":13,"fail":1,"skip":3}`

**Integrity (`GATES_BASE_REF=origin/main check-integrity.sh`):** 0 blockers, 1 warning (`.importlinter` apparatus edit — justified net-neutral edge removal).

---

## Per-Ticket Results

### AE-0107 — Single Write Owner: **WARN** (blocked by mutation gate)

| AC | Status | Evidence |
|----|--------|----------|
| All WO writes through single owner | **WARN** | Phase/sync/reviewer/resume-lock routed via `CarouselProjectWriteOwner` (`carousel_project_write_owner.py:77-147`). Routes commit via owner UoW (`editorial_workflow.py:160,217`). **Gaps:** (1) `editorial_finalize.py:127-128,152-153,207-210` still writes `status`/`error_message` via `repo.update_project` — documented deferral (`16c6df8`, comment at `:199-206`) for atomic terminal+presentation commit. (2) `nodes/images.py:381-390` still writes `phase_progress` via `repo.update_project`, not owner. |
| `lock_version` resume CAS preserved | **PASS** | Owner delegates unchanged to `OptimisticLockService.bump_carousel_version` (`carousel_project_write_owner.py:141-147` → `optimistic_lock_service.py:75-103`). Dual-CAS artifact path untouched (`carousel_artifact_build_repository.py:105-140`). Concurrent-resume: 66/66 green (`carousel_consolidation/`). |
| UoW single committer; routes no `db.commit()` for WO | **PASS** | No `db.commit()` in `editorial_workflow.py`. Resume runner uses `CarouselProjectWriteOwner(db).commit()` / `set_phase_status_and_commit` (`editorial_workflow_resume_runner.py:112,179,195`). |
| AE-0106 safety net diff=0 | **PASS** | `test_carousel_workflow_safety_net.py`: **19/19 passed**. Snapshots **not edited in Wave B** (`git diff f6e8f6d^..cee8a3a -- backend/tests/snapshots/editorial` = empty). |
| Gates + mypy + lint-imports + pytest | **FAIL** | mypy 476 files OK; lint-imports 14/0; carousel suite **720 passed**; **mutation gate FAIL**. |

### AE-0109 — Legacy Carousel ACL: **PASS** (implementation; blocked by mutation gate)

| AC | Status | Evidence |
|----|--------|----------|
| ACL sole editorial carousel-ORM importer | **PASS** | Editorial infra only: `legacy_carousel_acl.py` + `carousel_project_write_owner.py`. Editorial domain/application: 0 carousel-ORM imports. |
| Model ↔ EditorialProject/EditorialWorkflow; writes via owner | **PASS** | `legacy_carousel_acl.py:104-120` (read), `:134-178` (write delegation). Tests: `test_legacy_carousel_acl.py` 11 scenarios, all pass. |
| `lock_version` + checkpoint `thread_id=project_id` preserved | **PASS** | `legacy_carousel_acl.py:74-81,119,159-174`. Tests: `test_lock_version_surfaced_verbatim`, `test_checkpoint_thread_id_equals_project_id`, `test_bump_resume_lock_version_*`. |
| Editorial app/domain no direct ORM | **PASS** | Grep clean under `modules/editorial/domain` and `modules/editorial/application`. |
| mypy/lint-imports/pytest + safety net | **PASS** (impl) / **FAIL** (gates) | 22 editorial unit tests pass; safety net 19/19; mutation gate blocks. |

---

## Critical Wave-B Verifications

| Check | Result |
|-------|--------|
| Safety net byte-identical | **PASS** — 19/19; snapshots unedited in Wave B commits |
| Single write owner routing | **WARN** — core phase writes consolidated; `phase_progress` (images node) + terminal finalize `status`/`error_message` remain on legacy paths (one documented) |
| DDD placement + no override | **PASS** — owner in `modules/editorial/infrastructure/`; exposed via `public.py`; no pyproject overrides; no suppressions in owner/ACL |
| `Mapped[...]` typing (9 WO cols) | **PASS** — `carousel.py:61-93`: `status`, distribution sync cols, `assigned_reviewer_id`, `current_phase`, `phase_status`, `workflow_status`; nullability preserved |
| Dual-CAS `lock_version` | **PASS** — resume CAS delegated; artifact activation CAS unchanged |
| ACL sole ORM seam | **PASS** — 2 editorial-infra files only |
| Integrity / anti-gaming | **PASS** — 0 net-new blockers; `.importlinter` net-neutral (removed 1 grandfathered edge) |
| Full carousel suite | **PASS** — 720 passed |

---

## Findings

### 🔴 Blocker

1. **Mutation score below gate threshold** — `scripts/ci/mutation-score-gate.sh` — Score 62.30% < 75% (400 survived / 1965 mutants). CI will fail on merge.

### 🟠 Warnings

2. **`phase_progress` not routed through write owner** — `backend/src/rag_backend/application/services/carousel/nodes/images.py:381-390` — WO field `phase_progress` still mutated on entity + `repo.update_project`, bypassing `CarouselProjectWriteOwner`. AE-0107 scope lists `phase_progress` as workflow-owned.

3. **Terminal finalize still writes WO `status`/`error_message` outside owner** — `backend/src/rag_backend/application/services/carousel/editorial_finalize.py:127-128,152-153,207-210` — Documented deferral (`16c6df8`) for atomic presentation+terminal commit; strict AC wording says "ALL" WO writes. Behavior-preserving per safety net; track as known boundary.

4. **ACL module doc overstates ORM exclusivity** — `legacy_carousel_acl.py:5-6` says "only file" importing carousel ORM; `carousel_project_write_owner.py` also imports it (both editorial infra — acceptable, doc inaccurate).

### ⚪ Info

5. **DB-dependent gates skipped locally** — `test`, `diff-cover`, `migrations` — CI decides (expected without Postgres).

---

## Per-Dimension Summary

| Dimension | Status |
|-----------|--------|
| Gates (Phase 0) | ❌ FAIL (mutation) |
| Security | ✅ PASS |
| Code Quality | ✅ PASS |
| Mutation Testing | ❌ FAIL |
| Acceptance Criteria | 🟠 WARN |
| Orphan/Unfinished | ✅ PASS |
| Integrity / Anti-Gaming | ✅ PASS |

---

## Top 3 Risks

1. **Mutation gate failure will block CI** — 400 surviving mutants; likely weak assertions on new editorial infra paths.
2. **`phase_progress` bypass** — image-node writes still hit generic repo path; future consolidation risk if owner invariants tighten.
3. **Finalize terminal-write boundary** — documented but not fully aligned with strict "ALL WO writes" AC wording.

---

```json
{
  "verdict": "FAIL",
  "wave_id": "phase-4-wave-b",
  "iteration": 1,
  "findings": [
    {
      "id": "F-1",
      "severity": "critical",
      "ticket": "AE-0107",
      "file": "scripts/ci/mutation-score-gate.sh",
      "line": 0,
      "problem": "Mutation gate FAIL: score 62.30% is below the 75% threshold (400 survived mutants out of 1965).",
      "fix": "Strengthen tests for CarouselProjectWriteOwner and LegacyCarouselAcl mutation targets; re-run bash scripts/ci/gates.sh backend until mutation ≥75%."
    },
    {
      "id": "F-2",
      "severity": "warning",
      "ticket": "AE-0107",
      "file": "backend/src/rag_backend/application/services/carousel/nodes/images.py",
      "line": 381,
      "problem": "phase_progress (workflow-owned) is still written via repo.update_project, not CarouselProjectWriteOwner.",
      "fix": "Route _publish_progress_state through the write owner or document as explicit deferral with AC update."
    },
    {
      "id": "F-3",
      "severity": "warning",
      "ticket": "AE-0107",
      "file": "backend/src/rag_backend/application/services/carousel/editorial_finalize.py",
      "line": 207,
      "problem": "Terminal finalize persists status/error_message via repo.update_project outside the write owner (documented deferral for atomic presentation commit).",
      "fix": "Accept as documented boundary or refactor Phase 5 to split presentation terminal write from WO status atomically."
    },
    {
      "id": "F-4",
      "severity": "minor",
      "ticket": "AE-0109",
      "file": "backend/src/rag_backend/modules/editorial/infrastructure/legacy_carousel_acl.py",
      "line": 5,
      "problem": "Module doc claims sole carousel-ORM import; carousel_project_write_owner.py also imports CarouselProjectModel.",
      "fix": "Update docstring to name both editorial-infra ORM importers."
    }
  ],
  "summary": { "critical": 1, "warning": 2, "minor": 1 }
}
```

QA_VERDICT: FAIL

## Round 2 (confirmation) — PASS

I'm the independent QA reviewer for Phase 4 Wave B Round 2. Let me start by reading the QA agent skill, then systematically verify each of the 7 evidence items. I'll work within the read-only constraint (plan mode).
Now let me execute Phase 0 — the spine gates. Running the backend gates and integrity check simultaneously.
Phase 0 complete: **13 PASS / 0 FAIL / 4 SKIP** (lint-diff SKIP is expected without diff context in CI-like run). Integrity: **0 BLOCKERS / 1 WARN** (`.importlinter` modified — need to verify ticket justification).

Let me now verify all 7 evidence items in parallel. Starting with the key files and checks.
Excellent evidence from both subagents. Let me now directly verify a few critical items — the `.importlinter` change, the specific test counts, and run the test suites mentioned.
The `.importlinter` diff shows a LEGITIMATE tightening (removing an ignore rule because `editorial_workflow_resume_runner` no longer directly imports the carousel ORM — it goes through the write owner now). This justifies the apparatus-edit warning.

Let me verify the deferred boundary comment in the actual file and check the finalize diff more carefully.
Confirmed — the AE-0107 boundary comment exists at `editorial_finalize.py:199-206` and the Non-Goals section in the task file at line 35. Let me now run the two remaining test suites and verify the key integration tests.
All consolidation tests pass (66 passed). Now let me verify mypy and the full carousel test suite, plus check the `.importlinter` change justification.
Excellent! **mypy: Success (476 files)** and **720 carousel/workflow/editorial tests passed**. Let me do the final evidence checks.
All evidence is solid. Let me do one last check on the pyproject.toml diff and count the lock_version/carousel-related items.
Let me verify the git log for editorial_finalize.py at the correct path to confirm when the boundary comment was added.
All evidence collected. Let me compile the consolidated verdict.

---

# QA Validation Report — Phase 4 Wave B Round 2

## Phase 0 Gate Reproduction

| Gate | Status | Notes |
|------|--------|-------|
| `backend:format` | **PASS** | |
| `backend:lint` | **PASS** | |
| `backend:lint-diff` | **SKIP** | No diff context in this run |
| `backend:blanket-ignore` | **PASS** | |
| `backend:strict-diff` | **PASS** | |
| `backend:type` | **PASS** | mypy: Success (476 files) |
| `backend:imports` | **PASS** | 14 kept, 0 broken |
| `backend:arch-ratchet` | **PASS** | |
| `backend:docstrings` | **PASS** | |
| `backend:dead-code` | **PASS** | |
| `backend:bandit` | **PASS** | |
| `backend:pip-audit` | **PASS** | |
| `backend:integrity` | **PASS** | 0 BLOCKERS, 1 WARN (`.importlinter` tightening — justified) |
| `backend:test` | **SKIP** | No Postgres (CI decides) |
| `backend:diff-cover` | **SKIP** | No Postgres (CI decides) |
| `backend:migrations` | **SKIP** | No Postgres (CI decides) |
| `backend:mutation` | **PASS** | 79.43% > 75% threshold |
| **Summary** | **13 PASS / 0 FAIL / 4 SKIP** | |

## Per-Evidence Findings

### 1. Byte-identical ✅
- **19 test functions** in `test_carousel_workflow_safety_net.py` (lines 395-768) — confirmed via `grep -c`
- **All 7 snapshot files** under `tests/snapshots/editorial/` are **NEW additions** (AE-0106 safety net) — zero pre-existing snapshots were modified
- `editorial_finalize.py` change: ONLY the AE-0107 boundary comment added (commit `16c6df8` — docs-only, no logic changes)

### 2. Single write owner (AE-0107) ✅
All workflow-PHASE writes route through `CarouselProjectWriteOwner`:

| Write | Called from | Goes through |
|-------|-----------|-------------|
| `sync_phase()` | `editorial_workflow_service.py:195` | `CarouselProjectWriteOwner(db).sync_phase()` |
| `assign_reviewer()` | `editorial_workflow_service.py:146` | `CarouselProjectWriteOwner(db).assign_reviewer()` |
| `set_phase_status()` | `editorial_workflow_resume_runner.py:179,195` | `CarouselProjectWriteOwner(db).set_phase_status_and_commit()` |
| `bump_resume_lock_version()` | `editorial_workflow_routes_validate.py:218` | `CarouselProjectWriteOwner(db).bump_resume_lock_version()` |
| `commit()` | `editorial_workflow.py:160,217` / `resume_runner.py:112` | `CarouselProjectWriteOwner(db).commit()` (UoW) |

**Zero** `db.commit()` calls in the workflow service/runner/route files for these operations.

### 3. Documented deferral (F-1/F-2) ✅ — WITH JUSTIFICATION

**Location 1 — Code comment** (`editorial_finalize.py:199-206`):
> `# AE-0107 boundary: the terminal-finalization write persists the WO fields (status/error_message) ATOMICALLY with the deferred Phase-5 presentation columns (design_tokens/pdf_path/artifact_version) in this single repo.update_project commit. Splitting status out to CarouselProjectWriteOwner would break that atomicity (two commits) — so this terminal write stays on the legacy W1 persistence path per the AE-0105 field map until Phase 5 extracts presentation.`

**Location 2 — Task file Non-Goals** (`.agent/tasks/AE-0107-carousel-project-single-write-owner.md:35`):
> `OUT OF SCOPE (deferred, per the AE-0105 map): the atomic terminal-finalization write (...) remains on the legacy full-entity persistence path — splitting their WO-field writes out would break the single-commit atomicity (byte-identical).`

**Judge: Preserving single-commit atomicity is the CORRECT call.** The AE-0105 map (Section 2.3 WO fields + 2.4 DEF fields) shows `status`/`error_message` interleaved with `design_tokens`/`pdf_path`/`artifact_version` in the same `repo.update_project()` call. A two-phase write (WO owner + Phase-5 extract) would risk an intermediate inconsistent state or a partial failure. The boundary is now **explicitly documented** in both the code and the task file, with the AE-0105 map as the governing reference.

### 4. lock_version dual-CAS preserved ✅

**Resume CAS** (`carousel_project_write_owner.py:129-147`): Delegates **unchanged** to `OptimisticLockService().bump_carousel_version()` — byte-identical to pre-AE-0107 implementation.

**Artifact-activation CAS**: In `carousel_artifact_build_repository.py` (lines 105-140) — **untouched** (not in branch diff per `git diff --name-only`).

**Docstring confirmation** (line 136-139): *"the byte-identical resume CAS — so its expected-version contract and its pairing with the artifact-activation CAS (which keeps its own bump) are preserved exactly"*

**Concurrent-resume tests**: ✅ **66 passed** in `carousel_consolidation/` suite.

### 5. DDD + no override ✅

| Check | Result | Evidence |
|-------|--------|----------|
| Owner in `modules/editorial/infrastructure/` | ✅ | `carousel_project_write_owner.py` at correct DDD layer |
| No net-new app/api→infra import | ✅ | Only `workflow_state` (TypedDict) + `OptimisticLockService` (service) |
| Integrity 0 blockers | ✅ | `check-integrity.sh` confirmed 0 BLOCKERS |
| `pyproject.toml` unchanged | ✅ | 0-line diff vs origin/main |
| No mypy override added | ✅ | Pre-existing suppressions identical (8 before/after) |
| 9 columns Mapped[...] nullability | ✅ | `blog_markdown`, `caption`, `linkedin_post_pt`, `linkedin_post_en`, `status`, `assigned_reviewer_id`, `current_phase`, `phase_status`, `workflow_status` — all nullable preserved |

### 6. ACL (AE-0109) ✅ — sole carousel-ORM importers

| Importer | File | Layer |
|----------|------|-------|
| `CarouselProjectModel` | `legacy_carousel_acl.py:45` | Infrastructure (ACL) |
| `CarouselProjectModel` | `carousel_project_write_owner.py:45` | Infrastructure (Owner) |

- **Zero** carousel-ORM imports in editorial `domain/` or `application/`
- `lock_version` surfaced verbatim in ACL (line 71, 119)
- `checkpoint_thread_id` property preserved (lines 73-81)

### 7. Full verification suite ✅

| Tool | Result | Detail |
|------|--------|--------|
| `mypy -p rag_backend` | ✅ **Success** | 476 files, no issues |
| `lint-imports` | ✅ **14/0** | 14 contracts kept, 0 broken |
| `import_baseline.py --check` | ✅ **PASS** | Via arch-ratchet gate |
| `pytest -k "carousel or workflow or optimistic or editorial"` | ✅ **720 passed** | 1238 deselected, 0 failed |

### Integrity Apparatus Edit (.importlinter) ✅ (justified)

The 1 WARNING from `check-integrity.sh` is about `.importlinter` modification. The diff shows a **REMOVAL** of an ignore-rule:
```
- rag_backend.application.services.carousel.editorial_workflow_resume_runner → rag_backend.infrastructure.database.models.carousel
```
This is a **LEGITIMATE tightening**: the resume runner no longer directly imports `CarouselProjectModel` — it goes through the single write owner. The ticket (AE-0107) justifies this because the entire point is closing direct ORM access paths.

---

## Final Verdict

```json
{
  "verdict": "PASS",
  "wave_id": "phase-4-wave-b",
  "iteration": 2,
  "findings": [
    {
      "severity": "info",
      "file": "backend/.importlinter",
      "line": 204,
      "description": "Removed ignore-rule for editorial_workflow_resume_runner→CarouselProjectModel — legitimate tightening per AE-0107 (runner now goes through write owner)"
    },
    {
      "severity": "info",
      "file": "backend/.importlinter",
      "line": 204,
      "description": "Gates: 13 PASS (not 14) due to lint-diff SKIP — acceptable; the 3 DB-dependent SKIPs (test/diff-cover/migrations) are expected without Postgres"
    }
  ],
  "summary": {
    "critical": 0,
    "warning": 0,
    "minor": 0
  }
}
```

All evidence items verified:
1. ✅ Byte-identical: 19 tests, all snapshots new (none edited)
2. ✅ Single write owner: all 4 workflow-PHASE writes through `CarouselProjectWriteOwner`, no direct `db.commit()` bypass
3. ✅ Documented deferral: explicit AE-0107 boundary comment + Non-Goals section; atomicity is the correct justification
4. ✅ lock_version dual-CAS: resume CAS unchanged delegation + artifact CAS untouched
5. ✅ DDD + no override: owner in editorial/infrastructure, integrity 0 blockers, pyproject.toml untouched
6. ✅ ACL: only 2 carousel-ORM importers (both infrastructure), domain/application clean
7. ✅ Full suite: mypy Success (476 files), 720 tests passed

**QA_VERDICT: PASS**
