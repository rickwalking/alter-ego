# AE-0581 — Autopilot auto-cover for new carousels

Status: In Development
Tier: T1
Priority: High
Type: Feature
Area: Backend
Owner: Pedro Marins
Branch: hotfix/ae-0581-autopilot-auto-cover
Created: 2026-10-31
Updated: 2026-10-31

## Goal

When the autopilot starts a new carousel, it enqueues exactly one slide-1
cover generation through the existing Grok `images.edit` path
(ADR-0027), using the owner's current library photos as references.

## Problem

Autopilot carousels ship without a Grok cover unless the owner starts one by
hand on the web panel, so most autopilot runs never get a generated cover.

## Scope

- A standing consent setting (`AUTOPILOT_COVER_CONSENT`, default off): with no
  recorded consent the step skips and logs, and no photo ever leaves the app.
- The env passthrough so the switch can be turned on in prod: deploy.yml .env
  block (defaults 'false'), docker-compose.prod.yml backend and
  generation-worker services, and the parity gate lists it as a kill switch
  (added at the lead's merge review; it strengthens, never loosens, the gate).
- The owner's current photos are the newest library photos (newest first).
- A runner step that, after a queued run starts its carousel, records one
  pending cover generation (owner's library photos, up to 3, direction = the
  carousel topic) through `CoverGenerationService.start` and schedules the
  existing tracked background task.
- Existing caps (4 per carousel, 40 per month, one pending per carousel) and
  refusals are respected: a refusal or any failure skips and logs; the run is
  never affected.
- Tests + `.feature` file.

## Non-Goals

- No new prompts (the existing `cover_generation/v1` templates are used).
- No changes to the caps, the consent rules of the HTTP path, gates, deploy
  config, boost code or queue worker memory settings.
- No automatic picking of the generated cover (the owner still chooses).

## Acceptance Criteria

- [ ] An autopilot run with library photos and recorded consent enqueues
      exactly one cover job via `CoverGenerationService.start` +
      `schedule_cover_generation`.
- [ ] Cap/slot refusals skip the job with a log; the run continues normally.
- [ ] Without recorded consent the step skips and logs; no photos are read or
      sent.
- [ ] Without library photos the step skips and logs.
- [ ] Backend gates green (hotfix fast path: all gates except local mutation).

## Repro Steps

1. Let the autopilot start a queued run with a POV topic.
2. No cover generation is recorded for the new carousel.

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-10-31

Ticket created (hotfix, Pedro 2026-10-31). Renumbered AE-0580 -> AE-0581
(AE-0580 went to the hook-diversity hotfix after AE-0578/0579 landed in PRs
314/315). Implemented: `AUTOPILOT_COVER_CONSENT` standing-consent switch
(default off), the autopilot runner schedules one consent-gated cover job when
a fresh carousel starts, and the editorial facade helper
`schedule_autopilot_cover` runs the existing Grok images.edit path (library
photos, topic as direction, same caps and background task). Ships dark in prod
until the variable is added to the deploy env (deploy.yml untouched here per
the hotfix scope).

## Files Touched

- backend/src/rag_backend/infrastructure/config/settings.py
- backend/src/rag_backend/modules/autopilot/domain/cover_autostart.py (new)
- backend/src/rag_backend/modules/autopilot/infrastructure/cover_autostart.py (new)
- backend/src/rag_backend/modules/autopilot/application/runner.py
- backend/src/rag_backend/modules/autopilot/application/runner_deps.py
- backend/src/rag_backend/modules/autopilot/bootstrap.py
- backend/src/rag_backend/modules/autopilot/cover_constants.py
- backend/src/rag_backend/modules/editorial/infrastructure/carousel_cover_autostart.py (new)
- backend/src/rag_backend/modules/editorial/public.py
- backend/src/rag_backend/bootstrap/autopilot_worker_factory.py
- backend/tests/features/autopilot_cover_autostart_ae0581.feature (new)
- backend/tests/unit/modules/autopilot/test_cover_autostart_ae0581.py (new)

## Test Evidence

- 13 new unit tests: exactly one job with capped photos (3 of 4), fewer
  photos all go (newest first), cap refusal skips, no photos, no project,
  bridge unconfigured, non-POV refusal, no consent skips before photos are
  read (log-checked), consent calls the facade, facade crash is a logged skip,
  runner schedules once for a fresh project, a retried start delegates dedup,
  an existing generation row dedups without reading photos, a provider-outage
  start never schedules, cover error never fails the run.
- Postgres integration (real repo + CoverGenerationService + photo library):
  one pending job with the real photos, dedup on a second call, monthly-cap
  refusal through the helper.
- Backend gates green locally (hotfix fast path): format, lint, lint-diff,
  blanket-ignore, strict-diff, type, imports, arch-ratchet, docstrings,
  dead-code, inline-prompts, gherkin-refs, comments, blog-v1-dead-code,
  redis-factory, autopilot-env, healthcheck-loopback, openapi-fresh, bandit,
  pip-audit, integrity, duplication, test (full suite), diff-cover,
  migrations, schema-drift. mutation: deferred to CI (hotfix fast path).
- Two code reviews on the diff: first found a shared-session failure hazard
  and a retry-after-outage skip; both fixed (own session for the cover step,
  dedup by generation row) and verified clean on re-review.

## QA Report

Pending.

## Blockers

None.
