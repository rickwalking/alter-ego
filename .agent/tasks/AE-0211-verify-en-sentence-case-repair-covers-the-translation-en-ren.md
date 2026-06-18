# AE-0211 — Verify EN sentence-case repair covers the translation_en render source + regression test

Status: Intake
Tier: T1
Priority: Medium
Type: Quality
Area: backend
Owner: Unassigned
Branch: TBD
Created: 2026-06-18
Updated: 2026-06-18

## Goal

Guarantee EN slide render-source text is sentence-cased; close any gap the existing repair misses.

Source: Kaizen prod sweep `.agent/reports/kaizen-prod-2026-06-18.plan.md` (live carousel run, project b5b61790-9372-4a5a-ae17-30d2df28ef3d), validated by an independent architect cold-critic review.

## Problem

`presentation_validation.py:109 _validate_en_heading_case` (blocking) and `presentation_copy_repair.py:43 _repair_heading_sentence_case_en` already exist — yet prod carousel b5b61790 **still rendered all-lowercase EN headings/bodies** from `carousel_slides.extras.translation_en` (the render source), hot-patched manually 2026-06-18. The repair likely operates on `localized_slides` (proper-cased in the review) but NOT on the `translation_en` field the renderer consumes — a dual-representation gap.

## Scope

- Confirm whether the existing validation/repair covers `extras.translation_en` (the render-source); if not, wire it in.
- Add a regression test: a lowercase EN render-source heading is repaired (or blocked) before render.

## Non-Goals

- Re-implementing the repair (it exists) — only closing the render-source gap.

## Acceptance Criteria

- [ ] EN render-source (`translation_en`) headings/bodies are guaranteed sentence-cased before render.
- [ ] Regression test fails on a seeded lowercase `translation_en` heading.

## Repro Steps

1. ...

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

- Blocks: —
- Blocked by: —
- Related: presentation-policy validation/repair

## Progress Log

### 2026-06-18 HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
