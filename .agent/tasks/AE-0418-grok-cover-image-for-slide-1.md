# AE-0418 — Grok cover image for slide 1 (owner chooses per post)

Status: In Development
Tier: T2
Priority: High
Type: Feature
Area: Cross-cutting
Owner: Claude (developer lane)
Agent Lane: architect → developer → qa → release
Branch: feat/ae-0418-grok-cover
Kanban Card: TBD
Created: 2026-10-17
Updated: 2026-10-17

## Goal

GrokBot can upload a cover image for slide 1 and attach it to a topic, in every
mode (`news_analysis`, `pov`, `pov_news`). The owner's photo (POV) or the usual
Radar IA slide 1 stays the default; the owner switches to the Grok cover (and
back) with one Telegram tap, per post.

## Problem

Slide 1 is either the owner's photo (POV) or a generated hero image (Radar IA).
For news topics a real screenshot of the post or product, or an image Grok
generated for that exact topic, is often the better hook, but there is no way to
hand one over or to choose it.

## Scope

- `POST /api/autopilot/assets` (API key, shared rate limit): one PNG/JPEG
  `file`, `kind` (`ai_image` | `screenshot`), `source_url` for screenshots.
  Magic-byte check, size/dimension rules per kind, re-encode, stored as a
  creator asset with role `cover`.
- Topic field `cover: {asset_id}` with per-topic rejections
  (`cover_asset_unknown`, `cover_asset_expired`, `cover_asset_used`,
  `cover_source_invalid`, field `cover.asset_id`).
- Owner choice on Telegram: thesis message (POV modes) and review message
  (every mode) show the cover and a toggle button (`ap:cv:` / `ap:cvoff:`).
- Render: `ai_image` full-bleed under the title (POV hook and Radar IA intro);
  `screenshot` as a framed card with a source credit.
- Sweep of unreferenced covers older than 6 hours on the workers tick.
- Docs: `docs/architecture/grokbot-cover-asset.md` (copy of the fixed Grok
  contract), topics contract note, ADR-0024.

## Non-Goals

- Choosing the cover from the dashboard (see Decision Log D9).
- Any change to the Grok prompts or the scout itself.
- More than one cover per topic.

## Acceptance Criteria

- [ ] AC1 Upload accepts valid `ai_image` / `screenshot` files and answers 201 `{asset_id, kind, width, height}`.
- [ ] AC2 Upload rejects with `asset_too_large`, `asset_type_unsupported`, `asset_too_small`, `asset_kind_invalid`, `asset_source_missing` (4xx, `{"detail": code}`).
- [ ] AC3 `ai_image` is centre-cropped to 4:5 and must be ≥1080×1350 after the crop; `screenshot` keeps its aspect and must be ≥600 px wide; max 4096 px a side and 16 MP; metadata stripped by re-encoding.
- [ ] AC4 Cover assets are stored with role `cover` and never appear in the owner's hook photo library.
- [ ] AC5 A topic `cover` is accepted in every mode; the four per-topic reasons reject only that topic, with `field: "cover.asset_id"`; unknown keys inside `cover` are a batch 422.
- [ ] AC6 An asset is used by at most one topic (also within one batch).
- [ ] AC7 The cover is off by default: the carousel is created with the owner's photo / Radar IA slide 1.
- [ ] AC8 POV thesis message shows the cover and a "🖼️ Usar capa do Grok" button; the tap records the choice and the keyboard flips to "📸 Usar minha foto"; confirming builds the project with the chosen slide 1.
- [ ] AC9 The review message (every mode) shows the cover and the toggle; the tap re-renders slide 1 through the republish path (file staged first) and sends a fresh review with the opposite button.
- [ ] AC10 Cover taps are owner-only and idempotent; taps on a run in another state change nothing.
- [ ] AC11 `ai_image` renders full-bleed; `screenshot` renders as a framed card with `@handle · X` or the domain; a missing staged file raises `HookPhotoError(slide_cover_unreadable)`.
- [ ] AC12 Unreferenced covers older than 6 h are deleted (row, creator asset, file) by the workers tick.
- [ ] AC13 Manual prod SQL listed in the PR body (idempotent, nullable).

## Gherkin Scenarios

See `backend/tests/features/autopilot_grok_cover_ae0418.feature`.

## Delta

### ADDED

- `autopilot_cover_assets` table; `topic_candidates.cover_asset_id`; `autopilot_runs.cover_chosen`; `carousel_projects.slide_cover`.
- `POST /api/autopilot/assets`; Telegram callbacks `ap:cv:<run>` / `ap:cvoff:<run>`.
- Cover-card slide-1 layout and CSS.

### MODIFIED

- Topic intake schema/rules; thesis prompt and review keyboard; rework step; hook-face and intro strategies; creator asset library listing (excludes role `cover`).

### REMOVED

- Nothing.

## Affected Areas

- Backend: autopilot module, editorial facade seam, carousel template, creator assets.
- Frontend: none (Decision D9).
- Database: one table, three nullable columns (manual SQL on prod).
- API: new upload route, new optional topic field.
- Tests: unit + integration (fakes, no network).
- Docs: contract, ADR-0024, topics contract.
- Prompts/LLM: none.
- Observability: structlog events `autopilot.cover`.
- Deployment: manual SQL before merge.

## Dependencies

- Blocks: GrokBot sending covers.
- Blocked by: none.
- Related: AE-0406 (pov_news quotes), AE-0376 (hook photo), ADR-0020, ADR-0023.

## Implementation Plan

1. Feature file + ticket + ADR + contract doc.
2. Image validation (core), storage seam (editorial facade), autopilot store/table.
3. Upload route, intake rule, candidate column.
4. Run choice, Telegram buttons, rework step, project slide cover.
5. Render (ai_image / screenshot card), sweep.
6. Gates, mutation, QA, PR.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-17 10:00

Ticket created from the owner brief and the fixed Grok contract
(`ae-0418-grok-contract.md`).

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- **D1 — The Grok contract file is authoritative.** The orchestrator fixed the
  Grok-facing contract (`ae-0418-grok-contract.md`) and it is copied verbatim
  into `docs/architecture/grokbot-cover-asset.md`. Where the brief and the
  contract differ, the contract wins.
- **D2 — Storage.** The re-encoded WebP goes to the creator-asset storage as a
  `carousel_creator_assets` row with role `cover`, owned by the autopilot owner
  user. Autopilot metadata (kind, source URL, the topic that used it) lives in a
  new `autopilot_cover_assets` table whose id is the `asset_id` Grok receives.
  The owner's library list (role filter empty) excludes `cover` rows, and the
  hook-photo rotation already filters on role `hook`.
- **D3 — HTTP status per code.** `asset_too_large` 413, `asset_type_unsupported`
  415, `asset_too_small` / `asset_kind_invalid` / `asset_source_missing` 422.
  A missing `file` part is `asset_type_unsupported` (no PNG/JPEG was sent). A
  `source_url` that is not an http(s) URL counts as missing. A `source_url`
  sent with an `ai_image` is ignored.
- **D4 — "Used".** An asset becomes used when a topic that references it is
  stored (a new candidate). A topic refused for any reason, or a re-post of an
  existing candidate, leaves the asset free. Within one batch the first topic
  wins; the second gets `cover_asset_used`. A non-UUID `asset_id` is
  `cover_asset_unknown` (per topic), not a batch 422.
- **D5 — The cover rule runs last** among the per-topic rules (after the
  quotes), so an older rejection keeps its reason. The screenshot source is
  compared after `canonical_url`, the same normalisation the topic sources get.
- **D6 — Telegram presentation.** The cover is sent as a separate photo just
  before the thesis prompt / review keyboard message, so the existing text
  messages stay editable (`editMessageText`). The WebP is re-encoded to JPEG for
  Telegram. The review message offers the toggle in every mode (the brief asks
  for it on Radar IA's first review; for POV it is the second chance to change
  the thesis-time choice). Buttons: "🖼️ Usar capa do Grok", "📸 Usar minha
  foto" (POV), "↩️ Usar capa padrão" (Radar IA).
- **D7 — Switching after content exists** reuses the "Fix issues" mechanics: the
  tap moves `awaiting_owner → reworking` and queues rework phase `owner_cover`;
  the worker tick writes `carousel_projects.slide_cover` under the lock-version
  CAS (so the review revision changes), stages the file, re-renders through the
  republish path, and the normal final-review stop sends the fresh review.
- **D8 — Render.** `ai_image`: POV uses the existing full-bleed hook-photo
  markup with the cover as the image; Radar IA uses the intro artwork slot with
  the cover instead of `images/slide_1.jpg`. `screenshot`: a new `cover_card`
  strategy (dark background, title above, rounded/shadowed card, credit
  under). The credit is computed from `source_url` at selection time
  (`@handle · X` for x.com / twitter.com status URLs, else the host without
  `www.`).
- **D9 — Dashboard.** The dashboard's only slide-1 photo choice is the create
  wizard's "Foto do slide 1" (`use-pov-photo.ts`, manual carousels). Grok covers
  exist only on autopilot topics, so there is nothing to offer there; the
  per-run choice lives on Telegram. Frontend untouched (brief: "if the dashboard
  shows the slide-1 photo choice, include the Grok cover" does not apply to a
  flow that never has a Grok topic).
- **D10 — Sweep.** A new step on the Telegram notify tick (it already runs every
  worker cycle with a session) deletes up to 20 unreferenced covers older than
  6 h per tick: the cover row, its creator-asset row (only when role `cover`)
  and the stored file (only when no other row shares the content hash).
- **D11 — Schema.** Prod has no `alembic_version` and migrate-on-deploy is off:
  the PR body lists idempotent manual SQL; the Alembic revision is idempotent
  too (columns/table added only when missing).
- **D12 — Upload size reported.** An `ai_image` is centre-cropped to 4:5 and
  scaled to exactly 1080×1350 (the slide), so its 201 body reports 1080×1350;
  the contract's example matches this. A screenshot keeps its size.
- **D13 — Same bytes as an owner photo.** `carousel_creator_assets` is unique on
  (owner, sha256). If Grok re-sends bytes the owner already has, the existing
  row is reused with its role untouched, and the sweep never deletes a row whose
  role is not `cover` (nor a file another row still uses).
- **D14 — Contract check.** Everything in the fixed Grok contract is
  implemented as written (endpoint, fields, limits, 201 shape, codes, 6 h, one
  use). Nothing in it could not work. Backend-only details (HTTP status per
  code, 503 when no owner user is configured) are an appendix of the doc, not a
  change to the contract.

## Blockers

None.

## Final Summary

Pending.
