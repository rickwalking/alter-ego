# AE-0215 — Validate default image-provider key at startup

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

The default image-provider's API key is validated at startup so a default-preset carousel can't fail at image generation.

Source: Kaizen prod sweep `.agent/reports/kaizen-prod-2026-06-18.plan.md` (live carousel run, project b5b61790-9372-4a5a-ae17-30d2df28ef3d), validated by an independent architect cold-critic review.

## Problem

`constants/carousel.py:104-105` sets `IMAGE_MODEL_DEFAULT=gemini`, `IMAGE_STYLE_DEFAULT=comic_neon` (DB server_default also gemini/comic_neon), but prod `GEMINI_API_KEY` is empty. `app_factory` validates pinecone/openai keys for RAG but NOT the default image-provider key — so a carousel using the default preset would fail at image gen in prod.

## Scope

- Validate at startup that the configured/default image-provider has a usable key (fail fast or disable that preset with a clear message); or change the default preset to a provider with a configured key.
- Test: the default preset's provider key is required/validated.

## Non-Goals

- Procuring the Gemini key (ops decision).

## Acceptance Criteria

- [ ] Startup validation covers the default image-provider key (fail-fast or preset disabled).
- [ ] Test proves the default-preset provider key is validated.

## Repro Steps

1. ...

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

- Blocks: —
- Blocked by: —
- Related: AE-0119 (image provider ports)

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
