# AE-0555 — The generation worker releases the page cache of the carousel files it writes

Status: In Development
Tier: T2
Priority: High
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: ae-0555-worker-memory
Kanban Card: TBD
Created: 2026-10-26
Updated: 2026-10-26

## Goal

The generation worker's memory between carousel runs stays at its process baseline, and the images/export
peak no longer includes the files that earlier runs wrote.

## Problem

Prod, 2026-10-26: pgq jobs 24-28 ran one at a time through the generation worker (1600 MiB cgroup cap).
The worker's `memory.current` after each run was 669 → 843 → 858 → 925 → 966 → ~1035 MiB. `memory.peak`
went 772 → 1408 → 1442 → 1535 → 1600 MiB. `memory.events` showed `max=83` and `oom_kill=0`. Every step-up
happened in the images/export phase.

Findings, with measurements (see Test Evidence):

- The Python process does not leak in images/export. In the prod image (Python 3.11, Debian, 1 CPU,
  1600m cap), six 10-slide PT+EN cycles kept the process anon memory at 235-247 MiB and tracemalloc at
  3-10 MiB. Chromium and the Playwright driver exit after every export.
- The growth is page cache. Each run writes 116-224 MB of files: slides, HD slides, PDFs, the artifact
  staging copy and the promoted version (`du` of the 2026-10-26 carousels). Linux charges a write's page
  cache to the writer's cgroup, and the worker never reads those files again (the backend serves them).
  The per-run steps (+174, +15, +67, +41, +69 MiB) are no bigger than what each run writes. `max=83` with no
  OOM kill is the kernel reclaiming that cache at the cap.
- The fresh prod worker (after Pedro's restart) has anon 232 MiB and file 88 MiB.
- The export peak itself is headless Chromium. Measured per process in the prod image for one 10-slide
  HD export, the Chromium tree's anon+shmem was about 880 MiB (renderer plus display compositor), Python
  250 MiB and the Playwright node driver 85 MiB. The cgroup delta over the idle baseline was about 650 MiB
  for HD and about 480 MiB for standard. It barely depends on the slide count: 3 HD slides 660 MiB vs 10
  slides 700 MiB on the dev machine.
  `--disable-gpu`, `--disable-software-rasterizer`, `--num-raster-threads=1` and a device scale factor of
  1 did not lower it measurably. The device scale factor makes no difference because Playwright's
  `scale="css"` already captures at CSS pixels, so the output files were identical.

## Scope

- `release_page_cache(root)`: flush (`fdatasync`) and drop (`POSIX_FADV_DONTNEED`) the cached pages of a
  file or of every regular file under a directory. It skips failures per file, does not follow symlinks,
  and does nothing where the platform has no `posix_fadvise`.
- The slide export releases its output directory after the slides are written.
- The artifact activation (worker finalize, backend finalize) releases the whole project output tree
  after a successful activation.
- `backend/scripts/measure_carousel_export_memory.py`: the reproducible measurement.
- Update `.agent/reports/AE-0522.memory-budget.md` with the measured numbers.

## Non-Goals

- Raising the 1600 MiB cap, restarting the worker periodically, or recycling it after N jobs. Not needed:
  with the cache released, the measured idle baseline is flat.
- Lowering image resolution or dropping the HD export (a product call; not needed for the cap).
- `MALLOC_ARENA_MAX` or other allocator tuning: the measurement shows no Python-side growth.

## Acceptance Criteria

- [ ] AC1 A reproducible local measurement runs N carousel images/export cycles with fakes for paid calls
  and reports RSS/tracemalloc/cgroup memory per cycle, showing the growth before the fix and a flat
  baseline after it (numbers in Test Evidence).
- [ ] AC2 The images/export peak for a 10-slide carousel drops measurably, or the ticket explains with
  measurements what bounds it (Test Evidence).
- [ ] AC3 The fix is at the root (release what the worker wrote): no cap raise, no periodic restart.
- [ ] AC4 `.agent/reports/AE-0522.memory-budget.md` carries the new numbers.

## Gherkin Scenarios

`backend/tests/features/worker_page_cache_ae0555.feature`.

## Delta

### ADDED

- `rag_backend.infrastructure.external.page_cache.release_page_cache`.
- `backend/scripts/measure_carousel_export_memory.py`.

### MODIFIED

- `PlaywrightExportService.export_slides` releases its output directory after rendering.
- `CarouselArtifactBuildAdapter.build_and_activate` releases the project output tree after activation.

### REMOVED

- Nothing.

## Affected Areas

- Backend: slide export, artifact activation adapter.
- Frontend: none.
- Database: none (no schema change, no deploy one-shot).
- API: none.
- Tests: page cache unit tests and call-site tests.
- Docs: ticket, memory budget report.
- Prompts/LLM: none.
- Observability: a debug log for a file that could not be released.
- Deployment: none.

## Dependencies

- Blocks: none.
- Blocked by: none.
- Related: AE-0521, AE-0522 (memory caps and budget), AE-0542.

## Implementation Plan

1. Measure: per-phase prod log, prod cgroup split, per-process Chromium peak, local cycles in the prod image.
2. Gherkin and failing tests for the release helper and its two call sites.
3. Implement the helper and the call sites; re-measure in the prod image.
4. Update the memory budget; targeted tests, lint, types; CI on the PR.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-26

Measured, reproduced in the prod image, implemented the release at the two write sites.

## Files Touched

- `backend/src/rag_backend/infrastructure/external/page_cache.py`
- `backend/src/rag_backend/infrastructure/external/playwright_export.py`
- `backend/src/rag_backend/modules/presentation/infrastructure/editorial_workflow_ports.py`
- `backend/scripts/measure_carousel_export_memory.py`
- `backend/tests/features/worker_page_cache_ae0555.feature`
- `backend/tests/unit/infrastructure/test_page_cache_ae0555.py`
- `backend/tests/unit/infrastructure/test_page_cache_call_sites_ae0555.py`
- `.agent/reports/AE-0522.memory-budget.md`
- `.agent/reports/AE-0555.dev-summary.md`
- `.agent/reports/AE-0555.qa.md`

## Test Evidence

Pending.

## QA Report

`.agent/reports/AE-0555.qa.md`.

## Decision Log

- 2026-10-26 (Pedro): fix the retention at the root; no cap raise and no periodic self-restart as the fix.

## Blockers

None.

## Final Summary

Pending.
