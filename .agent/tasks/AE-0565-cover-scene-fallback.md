# AE-0565 — Cover scene search never drops the consecutive-round rule

Status: Review
Tier: T1
Priority: Medium
Type: Bug
Area: Frontend
Owner: Claude
Branch: fix/ae-0565-cover-scene-fallback
Created: 2026-10-27
Updated: 2026-10-27

## Goal

This is a follow-up to AE-0563 from the review of #298. The scene search gave up after 5000 steps and then fell back to a search with no previous round. That silently dropped the consecutive-round rule. A probe found 2 misses in about 8,600 round changes; for example, seed `uuid-56-x`, theme code, round 20 shared 4 values. Three rounds also kept only 3 of 6 new props, for example `uuid-33-x`, code, round 3. When the search failed completely, it could return an empty list.

## Acceptance Criteria

- [x] AC1 Before it drops the previous round, the search tries the seeded key and 7 alternative keys with fresh props only, then the same keys with any prop. This makes the rule hold in every tested round.
- [x] AC2 The last resort is a no-previous search with a large budget. If that also fails, the previous round is kept. Every round now returns six suggestions, and the result never becomes an empty list.
- [x] AC3 Rounds are computed by `catalogueRounds` (one chain); `catalogueScenes` reads its last round, and a negative round is clamped to 0.
- [x] AC4 Framing tags: only the wide shot and the full-body shot provide full body. Medium, three-quarter, side profile and low-angle knee-up no longer do.
- [x] AC5 Test widened to 60 seeds x 25 rounds x 6 themes (computed once, ~3 s), covering the two probe cases.

## Classification

Behavior-changing, under the AE-0563 scenarios in `frontend/tests/features/cover-prompt-coherence-ae0563.feature`. The scenarios are unchanged; only the guarantee is now enforced in every round.

## QA Checklist

- [x] `cover-prompt-scenes.test.ts` green over 9,000 rounds.
- [ ] CI green on the PR.
