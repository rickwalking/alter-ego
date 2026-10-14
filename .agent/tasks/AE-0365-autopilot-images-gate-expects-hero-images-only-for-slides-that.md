# AE-0365 — Autopilot images gate expects hero images only for slides that have one

Status: Dev Complete
Tier: T1
Priority: P0
Type: Bugfix
Area: backend
Owner: Claude Code (claude-opus-5-5)
Branch: fix/ae-0365-autopilot-hero-image-count
Created: 2026-10-14
Updated: 2026-10-14
Parent: AE-0348

## Goal

An autopilot run whose image phase produced one valid hero image per illustrated slide passes
the images gate and reaches `final_review`, instead of revising and escalating.

## Problem

Prod 2026-10-14, carousel `8e350d6e-78fc-436c-ab95-bed02535198b`. `image_assets` held 6 files,
`images/slide_1.jpg` to `slide_6.jpg`. Slide 7 is the CTA, rendered with the owner avatar, so it
has no hero image. `modules/autopilot/domain/policy.py` `_images` required
`len(snapshot.images) == snapshot.slides_total` (7). The gate revised, the image phase
regenerated (reused) the same 6, and the run escalated. Every real run failed here.

## Root cause

The image phase only illustrates `filter_image_slides(slides)`: slides whose `slide_type` is in
`IMAGE_SLIDE_TYPES` (intro, summary, content, closing) and that carry an `image_prompt`
(`application/services/carousel/nodes/images.py`). The CTA type is not in that set. The slides
come from the persisted carousel slides (`ensure_slides_from_outline`). The autopilot ignored
this contract and assumed one image per slide.

## Scope

- Editorial facade: `hero_image_total(slides)` and `CarouselAutomationAcl.hero_image_total
  (project_id)` count hero images with the image phase's own `filter_image_slides` on the
  persisted slides. A missing project, or no slides yet, gives 0.
- Autopilot: `SnapshotParts` / `GateSnapshot.hero_images_total`; `read_gate` fills it from the
  ACL; `_images` compares `image_assets` against it. 0 or more than `MAX_SLIDES` fails closed.
- The present / JPEG / decodable-size check per image is unchanged (a zero-byte file is not a
  JPEG and revises).
- Tests, Gherkin, and the gate line in `docs/architecture/grokbot-autopilot.md`.

## Non-Goals

- No migration. No change to the image phase or to which slides are illustrated.
- No prod action. Re-driving the escalated prod run is an owner action.
- The rework findings below are reported, not fixed (not small and safe).

## Acceptance Criteria

- [x] 6 hero images + a CTA slide (7 slides) → APPROVE.
- [x] 5 hero images (or 7) → REVISE `image_assets_invalid`.
- [x] A missing or zero-size file → REVISE `image_assets_invalid`.
- [x] No persisted slides (expected 0) or an out-of-range count → REVISE.
- [x] Integration test on the real editorial engine (real graph, checkpointer, run wrapper, real
  image phase with a fake image vendor): the autopilot approves outline, content, design and
  images and stops at `final_review` with `ready_for_owner`; the vendor wrote
  `slide_1..slide_6.jpg` only.
- [x] Gherkin scenarios in `backend/tests/features/autopilot_runner.feature`.
- [x] Python 3.11 import check.

## Repro Steps

1. Run the autopilot on a topic to the images gate (7-slide contract, OpenAI images).
2. The image phase stores 6 hero images; slide 7 (CTA) has none.
3. Before the fix: `decide()` returns REVISE `image_assets_invalid` (6 != 7), twice, then
   ESCALATE. Reproduced by the new integration test on the old policy
   (`images, revise, image_assets_invalid` at index 3).

## Rework investigation (owner tapped Rework on 8e350d6e)

Checked on the real engine with the same harness (revise at `final_review`, feedback
"make the hook punchier", `target_phase=content`):

- The feedback does reach content regeneration. `persist_phase_feedback` files the note under
  `phase_feedback["content"]` (target phase, AE-0288) and bumps `revision_count["content"]`;
  the graph routes back to `content`; `ensure_for_phase` sees the note, so
  `_ensure_content_artifacts` sets `should_regenerate=True` and calls `generate_slide_drafts`
  with `revision_notes` and `previous_drafts`. The run lands at `content/awaiting_human` with
  the lock bumped once. Target-phase mapping (Telegram `text` → `content`) is correct.
- Why it looked unchanged: the slides the owner sees (`pt/slide_N.jpg`) are only re-rendered
  at finalize, after the images gate is approved. After the rework the autopilot drives content,
  design and images again, and the images gate (this bug) revised and escalated every time, so
  finalize never ran and the old slides stayed. AE-0365 removes that blocker. If the content gate
  itself escalated, note that the rework consumed one content revision
  (`revision_count["content"]`), so a content gate already at its cap escalates on the first
  failed check.
- Real gap, follow-up (not fixed here): only the content phase reads `phase_feedback`. A
  Rework to **Outline** re-runs the node but `ensure_for_phase` only generates an outline when
  none exists; **Design** re-applies deterministic tokens; **Images** reuses images by
  generation key. So Outline / Design / Images reworks (and autopilot revises at the outline and
  images gates) re-run the node and produce the same artifacts. Fix needs the outline agent and
  image prompt to take revision notes and a cache bust; not a small, safe hotfix.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-14

Ticket created from the prod escalation. Fix + tests; new tests fail on the old policy (3 of
14) and pass on the fix. Hotfix fast path: every backend gate except mutation run individually
with the test Postgres `DATABASE_URL`; mutation deferred to CI. Python 3.11 import check: 706
modules, 0 failures. Moved to Dev Complete.

## Files Touched

- `backend/src/rag_backend/modules/editorial/infrastructure/carousel_automation.py`
- `backend/src/rag_backend/modules/autopilot/domain/gate.py`
- `backend/src/rag_backend/modules/autopilot/domain/snapshot.py`
- `backend/src/rag_backend/modules/autopilot/domain/policy.py`
- `backend/src/rag_backend/modules/autopilot/infrastructure/editorial_driver.py`
- `backend/tests/unit/modules/autopilot/test_hero_image_count_ae0365.py` (new)
- `backend/tests/integration/test_autopilot_hero_images.py` (new)
- `backend/tests/unit/modules/autopilot/test_slide_count_ae0362.py`
- `backend/tests/unit/modules/autopilot/test_gate_policy.py`
- `backend/tests/unit/modules/autopilot/test_autopilot_runner.py`
- `backend/tests/features/autopilot_runner.feature`
- `docs/architecture/grokbot-autopilot.md`

## Test Evidence

See `.agent/reports/AE-0365.dev-summary.md` (GATES_JSON line).

## QA Report

Pending.

## Blockers

None.
