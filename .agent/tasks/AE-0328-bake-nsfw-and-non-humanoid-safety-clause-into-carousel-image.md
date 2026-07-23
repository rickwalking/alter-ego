# AE-0328 — bake nsfw and non-humanoid safety clause into carousel image prompt composition

Status: In Development
Tier: T1
Priority: Medium
Type: Quality
Area: backend
Owner: Unassigned
Branch: TBD
Created: 2026-07-22
Updated: 2026-07-22

## Goal

Carousel image prompts always carry a safety clause so `custom_visual_details`
cannot steer generation into moderation-risky or NSFW humanoid output,
regardless of the project's visual direction text.

## Problem

Prod incident 2026-07-22 on project `ee540af1` (kaizen supplemental S2): slide 3
of a published carousel contained nudity. Root cause: the project's
`custom_visual_details` ("Ghost in the Shell…") steers generation toward female
holograms, and "glowing AI entity"-style scene prompts leave body form
unconstrained. Regeneration attempt 1 (clothing constraints) still produced body
contours and was rejected on visual inspection; attempt 2 forcing NON-HUMANOID
form ("abstract geometric shards, no body/face/torso") produced a clean result.
Related precedent: the neo_anime preset already needed a modesty clause for the
same OpenAI output-moderation false-positive class (2026-06-23). Instance was
fixed by hand; the class is unenforced — nothing prevents the next
`custom_visual_details` from steering another slide into the same failure.

## Scope

- Bake a safety clause into the image prompt composition path (the
  `_compose_scene`/style-wrap layer where brand lock and `custom_visual_details`
  are folded in), applied to EVERY slide prompt across presets — not per-preset
  hand patches.
- Clause direction (tune during dev): depictions of people must be modest/fully
  clothed; when the scene is an abstract/AI/energy entity, force non-humanoid
  form (no body, face, or torso contours).
- Unit test asserting the clause is present in composed prompts for every
  preset, including when `custom_visual_details` is set.

## Non-Goals

- No changes to image provider routing or preset palettes.
- Not a content-policy filter on user text — only a prompt-side guard on the
  generated image.

## Acceptance Criteria

- [ ] Every composed slide image prompt contains the safety clause, across all
      presets, with and without `custom_visual_details` (parameterized test).
- [ ] The clause survives revision-feedback prompt rebuilds (feedback append
      path).
- [ ] Seeded test: a `custom_visual_details` string steering toward humanoid
      character art still yields a composed prompt carrying the non-humanoid/
      modesty constraint (AE-0180-style proof the guard fires where it matters).
- [ ] Existing prompt snapshot/golden tests updated in the same change;
      `.feature` scenario for the prompt-composition behavior change (AE-0153).

## Repro Steps

1. Create a project with `custom_visual_details` referencing humanoid character
   aesthetics (e.g. "Ghost in the Shell style").
2. Generate images for an "AI entity" scene slide.
3. Today: no prompt-side constraint on body form; output can contain nudity or
   trip output moderation (observed in prod 2026-07-22).

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests

## Dependencies

None.

## Progress Log

### 2026-07-22

Ticket created by kaizen session-2026-07-22 (supplemental S2, user-approved).
Plan: `.agent/reports/kaizen-session-2026-07-22.plan.md`.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
