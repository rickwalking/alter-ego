# AE-0563 — Coherent, fresh cover prompt reshuffles

Status: Review
Tier: T1
Priority: High
Type: Bug
Area: Frontend
Owner: Claude
Branch: fix/ae-0563-cover-prompt-coherence
Created: 2026-10-27
Updated: 2026-10-27

## Goal

Pedro (2026-10-27) asked to finish the cover prompt variety work of AE-0562 after reviewing it in production.

## Problem

Prod evidence on carousel 2fe43d2c (2026-10-27): within one set nothing repeats, no hex, no quoted title. However:

1. "Outras ideias" reshuffled only partly. 4 of the 6 new suggestions kept the angle + wardrobe + location of a previous suggestion, and the 6 props were the same 6 props reassigned (the theme pool only had 6).
2. Combinations did not fit together because each pool was picked on its own: harsh midday sun in a metro station, "adjusting the jacket collar" with a linen shirt, a toy robot "on the desk" on a cobblestone street, a face close-up that "sits on stairs".

## Acceptance Criteria

- [x] AC1 Compatibility rules (`constants/cover-prompt-compat.ts`): locations provide indoor/outdoor, surface, railing, stairs; lights need indoor or outdoor (or neither); poses need a railing, stairs, a jacket collar or a full-body framing; close-up and half-body shots do not provide full body; desk/table props need a surface and wall/board props need indoor. Only combinations whose needs are all met are suggested.
- [x] AC2 Picking is a seeded depth-first search (`cover-prompt-scenes.ts`): deterministic per seed + theme + round. The next compatible option in seeded order is the fallback, with a bounded step budget.
- [x] AC3 Round N > 0 is derived from round N-1: no new suggestion shares more than one dimension value (location, shot, wardrobe, pose, light, prop) with any suggestion of the previous round.
- [x] AC4 Theme prop pools grow to 12 per theme (pt/en). A new round first tries only props unused in the previous round, then falls back to unused-first ordering. Measured over 200 seeds x 7 rounds x 6 themes, 99.9% of rounds bring at least 4 new props and most bring 6.
- [x] AC5 Kept: six pairwise distinct suggestions per set, no hex, no quoted title, 400-char cap, no AI call on "Outras ideias".
- The park and bookshop locations now mention a picnic table and a reading table, which gives four locations with a surface for desk props.

## Classification

Behavior-changing, so a `.feature` is required: `frontend/tests/features/cover-prompt-coherence-ae0563.feature`.

## QA Checklist

- [x] `cover-prompt-scenes.test.ts`: compatibility over 40 seeds x 6 rounds x 6 themes, the four prod incoherent scenes rejected, ≤1 shared value between consecutive rounds, prop novelty and pool size 12, pairwise distinct, deterministic, no hex.
- [x] `cover-prompt-catalogue.test.ts` (AE-0562 behaviour) still green.
- [ ] CI green on the PR.
