# AE-0037 — Managed Creator Branding Assets

Status: Review
Tier: T2
Priority: High
Type: Feature
Area: Backend/API
Owner: Unassigned
Agent Lane: developer -> qa -> release
Branch: feat/ae-0037-creator-assets
Kanban Card: TBD
Created: 2026-06-09
Updated: 2026-06-09

## Goal

Replace fragile creator avatar paths with authenticated, managed, validated creator assets that can be staged into versioned carousel artifacts.

## Problem

CTA rendering currently assumes a relative avatar exists under each output tree. Broken avatar paths can render silently, and accepting arbitrary paths or URLs would introduce security risk.

## Scope

- Add owner/admin upload, select, replace, and remove endpoints for creator assets.
- Validate multipart uploads for MIME, magic bytes, decoder agreement, size, pixels, animation, decompression bombs, EXIF, orientation, and path containment.
- Normalize accepted assets to single-frame sRGB WebP with content-addressed filename.
- Add `CreatorAssetService` for staging assets into candidate artifacts.
- Reject new `creator_avatar_url` writes and report external legacy URLs without fetching them.
- Add tests for valid, oversized, animated, MIME-mismatched, decompression-bomb, truncated, and unauthorized cases.

## Non-Goals

- Remote URL import.
- Arbitrary local path ingestion.
- Artifact activation, which is AE-0038.

## Acceptance Criteria

- [ ] WHEN a creator asset is uploaded or selected THE API SHALL require owner or admin access.
- [ ] WHEN upload input is a URL or client local path THE API SHALL reject it and SHALL perform no network request.
- [ ] WHEN a file has invalid MIME, magic bytes, dimensions, animation, decompression risk, or truncation THE API SHALL reject it.
- [ ] WHEN a valid creator asset is accepted THE SYSTEM SHALL normalize it to content-addressed WebP and store metadata.
- [ ] WHEN CTA rendering uses configured branding THE SYSTEM SHALL stage and decode the managed asset or fail export with a precise code.

## Gherkin Scenarios

```gherkin
Feature: Versioned carousel presentation contract

  Scenario: Unauthorized user cannot change creator branding
    Given a user is neither project owner nor admin
    When the user selects or uploads a creator asset
    Then the API returns forbidden
    And project branding is unchanged

  Scenario: Remote creator URL is rejected
    Given an owner submits creator_avatar_url with an HTTPS or private address
    When the creator branding API validates the request
    Then the API rejects the unmanaged URL
    And performs no network request
```

## Delta

### ADDED

- Creator asset API endpoints and service.
- Upload validation and normalization.
- Asset staging into candidate artifacts.
- Security-focused unit tests.

### MODIFIED

- Carousel project creator branding fields.
- CTA renderer asset resolution.
- API schemas for creator branding.

### REMOVED

- New writes to unmanaged `creator_avatar_url`.
- Remote or local path ingestion for creator assets.

## Affected Areas

- Backend: yes
- Frontend: yes
- Database: yes
- API: yes
- Tests: yes
- Docs: no
- Prompts/LLM: no
- Observability: yes
- Deployment: yes

## Dependencies

- Blocks: AE-0038, AE-0039
- Blocked by: AE-0030
- Related: AE-0031, AE-0035

## Implementation Plan

1. Add creator asset service and API endpoints.
2. Implement upload validation and WebP normalization.
3. Enforce owner/admin authorization.
4. Stage assets into candidate artifact assets.
5. Add migration tests and security tests.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-06-09

Ticket created from AE-0028 architecture plan.

## Files Touched

Pending.

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- Remote creator import requires a separate future security review.

## Blockers

Blocked by AE-0030.

## Final Summary

Pending.
