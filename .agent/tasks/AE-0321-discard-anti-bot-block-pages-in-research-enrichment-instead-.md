# AE-0321 — discard anti-bot block pages in research enrichment instead of treating them as source content

Status: Ready
Tier: T1
Priority: Medium
Type: Bugfix
Area: backend
Owner: Unassigned
Branch: TBD
Created: 2026-07-18
Updated: 2026-07-18

## Goal

A CDN/anti-bot block page returned by a scraped URL source is discarded (the
source keeps its original URL content, with a warning log) instead of becoming
a "research finding".

## Problem

Observed live 2026-07-18 on prod (project f9e3e199): scraping
https://x.ai/news/grok-4-5 returned a Cloudflare "you have been blocked" page,
which the synthesis agent dutifully summarized into a research finding about
Cloudflare. Block pages are recognizable by stable markers and should never
reach synthesis.

## Scope

- `_scrape_one` (agents/research_enrichment.py): after sanitization, scan the
  head of the text for block-page markers (case-insensitive, constants in
  `domain/constants/research_enrichment.py`); on a hit log
  `research_url_block_page` and return None (graceful degradation, same as a
  failed scrape).
- Feature scenario + unit tests (marker hit, marker deep in body not a hit,
  normal page unaffected).

## Non-Goals

- Do not refactor unrelated code
- ...

## Acceptance Criteria

- [ ] A scraped page matching a block-page marker in its head is discarded; the source keeps its original URL content.
- [ ] research_url_block_page warning is logged with the URL.
- [ ] Markers deep in a legitimate page body do not trigger the detection.
- [ ] Normal pages are unaffected.

## Repro Steps

1. Start an editorial workflow with a url source behind Cloudflare bot
   protection (e.g. x.ai).
2. Observe the research findings summarizing the block page text.

## Affected Areas

- [ ] Backend
- [ ] Frontend
- [ ] Tests

## Dependencies

None.

## Progress Log

### 2026-07-18 HH:mm

Ticket created.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Blockers

None.
