# AE-0546 — Approving a carousel for publishing wipes its caption; the autopilot posts captionless

Status: In Development
Tier: T1
Priority: Critical
Type: Bug
Area: Backend
Owner: Claude Code (claude-opus-5-5)
Agent Lane: developer → qa → release
Branch: fix/ae-0542-approve-keeps-caption
Kanban Card: TBD
Created: 2026-10-24
Updated: 2026-10-24

## Goal

Approving a carousel for publishing never clears or overwrites its saved caption, and no Instagram publish path ever
posts an empty caption.

## Problem

On prod, approving carousel `5350e0ca-ad31-40a1-9e50-70852f1ee484` from Telegram ("Publicar agora": run
`awaiting_owner` → `publishing` with `owner_approved`, then the editorial approve that sets
`workflow_status=approved_for_publish` and makes the carousel public) emptied `carousel_projects.caption` (657 chars
→ empty) at about 03:13 UTC on 2026-10-24. The autopilot worker then posted to Instagram with an empty caption.
Pedro's text survives in `content_versions` (`carousel_copy`, version 2, field `caption`). This blocks the 08:00 BRT
autopilot posts.

Root cause (reproduced by `test_publish_now_keeps_the_saved_caption_and_posts_it`, which fails on `main`; prod
evidence query: `.agent/reports/AE-0546.prod-evidence.sql`):

1. `create_generation_draft` (blog "from carousel", ADR-0025) creates the carousel's `origin='carousel'` blog row
   with `distribution={}`. That row is the carousel's canonical distribution home (ADR-0011).
2. `PostgresCarouselRepository._overlay_distribution` overlays the home's values on every loaded carousel, so the
   loaded entity gets `caption=None` although the column holds the saved text.
3. The public release on approval (`LegacyPublishingAcl.release_public` → `repo.update_project`) saves that entity:
   `carousel_projects.caption` becomes `None` and the mirror writes `None` into the home too.
4. The publish job reads the empty caption and posts it; nothing refused an empty caption on this path.

Second issue: a workflow whose run died after the images gate, before `final_review` opened its review, reports
`final_review/approved` exactly like an approved carousel held at `approved_hold`. `final_review` is in
`NEVER_PARKED_PHASES`, so the runner waited forever (`action: wait`).

## Scope

- `carousel_repository._overlay_distribution`: a field the home has never received (`None`) keeps the saved column
  value; an explicit value (including `""`, a deliberate clear) still wins.
- `create_generation_draft`: a `from-carousel` draft starts with the carousel's saved caption and LinkedIn posts.
- Instagram publish refuses an empty or blank caption (`instagram_caption_empty`): the autopilot worker fails the run
  with that reason and the Telegram notice (retry offered); the manual publish refuses before any Graph call. The
  manual HTTP route already refused an empty saved caption (409 `caption_missing`).
- `LegacyPublishingAcl.release_public`: one targeted `UPDATE carousel_projects SET is_public, current_phase WHERE id
  AND lock_version = seen` (compare-and-set, `version_conflict` when it matches no row) instead of saving the whole
  carousel loaded earlier, so a caption edit landing between the load and the release is kept.
- `InstagramPublishJob.publish_claimed` (the owner route on a claimed run, atomic path) re-checks the caption.
- Parked guard: `GateStatusInput.node_pending` (the engine's `is_parked_before_node`); a never-parked phase is parked
  when the engine still has a node pending with no open review, so the runner re-drives it after the grace period.

## Non-Goals

- Repairing prod data (the caption of `5350e0ca` is restored from its copy version 2 by Pedro in the dashboard).
- Editing the captionless Instagram post.

## Acceptance Criteria

- [x] AC1 Given a carousel with a saved caption and either a blog draft created from it or a carousel-origin blog
  row stored with `distribution={}` (the prod shape), When the owner taps "Publicar agora", Then the run is
  publishing, the carousel is approved and public, the caption is unchanged in the row and as the app loads the
  carousel, and the Instagram post carries it.
- [x] AC2 Given a carousel whose blog row has an empty distribution, When it is loaded and saved, Then the saved
  caption is kept (and mirrored); an explicitly cleared caption stays cleared.
- [x] AC3 A blog draft created from a carousel starts with the carousel's saved copy.
- [x] AC4 The autopilot worker fails a run with an empty or blank caption (`instagram_caption_empty`, Telegram notice
  with retry) without calling Instagram; the manual publish refuses it.
- [x] AC5 A workflow stuck before the final review interrupt is re-driven after the grace period; an approved, held
  carousel is still never parked.
- [x] AC6 The public release writes only `is_public` and `current_phase`, guarded by `lock_version`; a caption saved
  after the carousel was loaded survives the release.

## Gherkin Scenarios

`backend/tests/features/approve_keeps_caption_ae0546.feature`.

## Affected Areas

- Backend: `infrastructure/database/carousel_repository.py`, `infrastructure/database/blog_generation_drafts.py`,
  `domain/constants/instagram_publish.py`, `modules/autopilot/domain/publish.py`,
  `modules/autopilot/application/publish_steps.py`, `modules/autopilot/application/manual_publish.py`,
  `modules/autopilot/domain/parked.py`, `modules/autopilot/infrastructure/editorial_driver.py`,
  `modules/autopilot/application/publish_job.py`, `modules/publishing/infrastructure/legacy_publishing_acl.py`.
- Database: no schema change.
- Tests: integration (publish now end to end), unit (repository/draft, empty-caption guard, stuck final review).

## Dependencies

- Blocks: the 08:00 BRT autopilot posts.
- Related: ADR-0011 (distribution home), ADR-0025 (blog drafts), AE-0363 (parked guard).

## Decision Log

- 2026-10-24: a `None` field in the distribution home means "never mirrored", not "cleared"; the saved column value
  is kept and the next save mirrors it, which also heals existing prod rows created with `{}`.
- 2026-10-24: an empty caption is a permanent pre-check failure with retry offered (the owner can fix the caption and
  retry).

- 2026-10-24: renumbered from AE-0542 (PR #274 holds that id), then from AE-0545 (PR #279 opened first with it).
- 2026-10-24: the release does not bump `lock_version`; bumping it would fail the workflow resume CAS that follows
  an approval. The CAS still refuses a write when a concurrent writer bumped the version.

## Blockers

None.
