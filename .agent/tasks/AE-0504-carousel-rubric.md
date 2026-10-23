# AE-0504 — Select a rubric for carousel generation and show its scores

Status: Dev Complete
Tier: T3
Priority: Medium
Type: Feature
Area: Backend + Frontend
Owner: Pedro Marins
Branch: feat/ae-0504-carousel-rubric
Created: 2026-10-22
Updated: 2026-10-22

## Goal

The owner picks a quality rubric per carousel in the create wizard; its criteria steer the content draft
and, after drafting, each criterion is scored (0-100) against its threshold, stored, and shown in Revisão
final.

## Problem

Dashboard QA (DQ-A-08): rubrics can be created and evaluated ad hoc on `/dashboard/rubrics`, but nothing
connects them to generation. `carousel_projects.rubric_id` exists (ORM and prod) but no route sets it; the
content-draft prompt only carries the presentation contract's checklist; no workflow step evaluates a
carousel against a rubric, so the final review "Qualidade" tab is always empty and the analytics quality
tile (AE-0497) has no content scores. Deleting a rubric that something references fails with an
unhandled foreign-key error (500).

## Scope (Pedro, 2026-10-22, Q12: per carousel in the wizard, default = the default rubric; criteria in
the generation prompt + scores shown afterwards; new rubric_id column via a deploy one-shot; no automatic
rewrite)

- `carousel_projects.rubric_id` already exists in the ORM, in the Alembic baseline and in prod (checked
  read-only on 2026-10-22), so no schema change or one-shot is needed for it.
- `POST /api/carousels` accepts `rubric_id`; a missing one takes the default carousel rubric (when there
  is one); an unknown rubric is 404, one not applicable to carousels 422. The project response returns it.
- Content drafting appends the rubric's criteria (name, description, guidance prompt, scale, threshold)
  to every content prompt (generic, Radar, POV, POV news) from a new prompt file
  (`carousel_rubric/v1`), leaving the existing prompt versions untouched.
- After the drafts are written, one scoring call (reasoning model, structured JSON, the 0-100 scale stated
  in the prompt) scores each criterion; the result is in the workflow state's `rubric_scores` and stored
  in `rubric_evaluation_scores` (carousel id, rubric id, per-criterion scores, rounded 0-100
  `overall_score`, passed). A regeneration replaces the carousel's row. No rewrite pass.
- Revisão final "Qualidade" shows the rubric, each criterion's score vs its threshold, and flags the ones
  below threshold.
- Deleting a rubric used by a carousel is refused with 409 naming the carousels (no broken reference).
- Analytics: content quality averages only the caller's own carousels' scores for non-admins (the
  `blog_post_quality.py` pattern); admins see all.

## Non-Goals

- An automatic revise pass when a criterion is below threshold (Pedro: no automatic rewrite).
- Rubric ownership (rubrics are global today; see Open Questions).
- Re-scoring after manual slide edits.

## Acceptance Criteria

- [x] Given the create wizard, Then a "Rubrica" selector lists the rubrics applicable to carousels with the
      default preselected, and "Política padrão" (no rubric) as an option; the choice is sent as
      `rubric_id`.
- [x] Given `POST /api/carousels` without `rubric_id`, Then the default carousel rubric is stored; with an
      unknown id 404; with a rubric not applicable to carousels 422.
- [x] Given a carousel with a rubric, When content is drafted, Then every content prompt variant carries
      the rubric's criteria (name, description, prompt, scale, threshold) — unit test on the rendered
      prompt; a Langfuse trace from the evidence run in the PR.
- [x] Given drafted content, Then each criterion is scored on 0-100, the scores are in `rubric_scores`
      and in one `rubric_evaluation_scores` row for the carousel (rubric id, rounded `overall_score`);
      a regeneration replaces that row; a scoring failure leaves the workflow running with no scores.
- [x] Given Revisão final, Then "Qualidade" shows each criterion's score vs threshold and flags those
      below it.
- [x] Given a rubric used by a carousel, When it is deleted, Then 409 names the carousels and nothing is
      deleted.
- [x] Given a non-admin, Then the quality average counts only their own carousels' scores; an admin's
      counts all.
- [ ] Evidence for Pedro: one generated carousel scored against the QA rubric (needs Pedro's go-ahead for
      the paid run).

## Gherkin Scenarios

See `backend/tests/features/carousel_rubric_ae0504.feature` and
`frontend/tests/features/carousel-rubric-ae0504.feature`.

## Affected Areas

- [x] Backend (carousel create schema/route, content draft agent, rubric scoring service + prompt, phase
      artifact runner, rubrics delete route, analytics projection)
- [x] Frontend (create wizard selector, final review quality tab, i18n)
- [x] API (`rubric_id` on create/response; OpenAPI artifact)
- [x] Tests
- Database: no change (`carousel_projects.rubric_id` exists).

## Dependencies

- Related: AE-0497 (quality tile reads `rubric_evaluation_scores`), AE-0498 (rubric needs a criterion).

## Open Questions

- Which rubrics the wizard lists (rubrics have no owner): asked Pedro; building with "every rubric
  applicable to carousels" until answered.
- The paid evidence run: asked Pedro.

## Progress Log

### 2026-10-22

Ticket written from the dashboard QA triage and the code map. Prod checked read-only:
`carousel_projects.rubric_id` exists; `rubric_evaluation_scores` is empty.

## Files Touched

See `.agent/reports/AE-0504.dev-summary.md`.

## Test Evidence

Full backend (with Postgres) and frontend gate captures green; mutation in CI. The evidence run waits for
Pedro's go-ahead. See the dev summary.

## QA Report

## Blockers

None.
