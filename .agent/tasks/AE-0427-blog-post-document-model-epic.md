# AE-0427 — Blog post document model epic (posts own structure, voice and images)

Status: Intake
Tier: T3
Priority: High
Type: Epic
Area: Cross-cutting
Owner: Unassigned
Agent Lane: planner → architect → developer → qa → release
Branch: TBD (one branch per child)
Kanban Card: TBD
Created: 2026-10-18
Updated: 2026-10-18

## Goal

Make a blog post its own document that owns its structure, its voice and its images, so posts read
like the owner wrote them and use real generated images instead of Instagram-card screenshots.
Architecture: [ADR-0025](../../docs/decisions/0025-blog-post-owns-structure-voice-and-images.md) and
[docs/architecture/blog-post-document-model.md](../../docs/architecture/blog-post-document-model.md).

## Problem

A carousel-origin blog post is a read-time view over carousel data: the body is a mechanical join of
`long_form_notes` with no persona (QA F-02/F-03), in-body images are the rendered slides with
baked-in text (F-01/F-07), the editor is one markdown textarea with no images or versions
(F-06/F-12/F-13/F-15), there is no generation entry point (F-09/F-11), and `ai-suggest` returns a
fenced JSON envelope (F-10). Full evidence: `~/alter-ego-qa/2026-10-18-blog/REPORT.md`.

## Scope

Coordinate AE-0422 through AE-0426 plus AE-0428 in dependency order:

- **Wave A — AE-0422:** public blog stops rendering carousel slides; retire the stale slide specs;
  hide **all** published carousel-origin posts (origin+status sweep, durable marker). Ships first
  and alone.
- **Wave B — AE-0423:** `blog.v2` document model + one-shot v1→v2 **cutover command** (PT + every
  translation; v1 writes dropped; temporary read fail-safe) + explicit deploy step + public v2
  render + public PT/EN content switch. Independent of Alembic heads/stamp.
- **Wave C — AE-0424:** section editor, per-section/cover images, PT/EN language buttons, versions on
  save, unsaved guard, review/schedule/publish, strict `ai-suggest`.
- **Wave D — AE-0425:** blog writer in the persona voice + quality gate + GPT cover/section images
  (count = carousel `slide_count`) + from-carousel and standalone generation, executed by a tracked
  in-process task with lease/heartbeat/timeout and a restart reaper.
- **Wave E — AE-0426:** rebuild all marker-selected hidden rows as drafts through the D pipeline.
- **Wave F — AE-0428:** delete the dead blog-v1 files and drop `blog_image_map` end-to-end; remove
  the Knip baseline entries and add the no-regression guard.

## Non-Goals

- Owner photo upload (`source: "upload"` reserved only).
- Rewriting the carousel pipeline (frozen, ADR-0007/0021); only the blog-only `blog_image_map` field
  is removed (AE-0428), not the carousel features.
- Multi-author/multi-tenant concerns (ADR-0009 §1).

## Acceptance Criteria

- [ ] WHEN a carousel-origin blog is generated THE SYSTEM SHALL always create a draft (never publish).
- [ ] WHEN the public blog renders THE SYSTEM SHALL show each section with its own generated image
      and non-empty alt, and SHALL NOT show any `/slide-images/` carousel slide.
- [ ] WHEN a blog body is generated THE SYSTEM SHALL apply the persona voice guide and store a
      voice score `>= 70` (or perform exactly one rewrite pass).
- [ ] WHEN the owner edits a post THE SYSTEM SHALL allow per-section editing and add/remove/replace
      of the cover and each section image.
- [ ] WHEN the owner switches PT/EN THE SYSTEM SHALL show and save the corresponding document
      subtree (EN falls back to PT when absent) in the editor and on the public page.
- [ ] WHEN the owner submits for review, approves/rejects, schedules or publishes THE SYSTEM SHALL
      enforce the existing status guards and show the resulting state.
- [ ] WHEN a carousel-origin post is generated THE SYSTEM SHALL create one section per slide
      (`len(sections) == project.slide_count`) and `slide_count + 1` images.
- [ ] WHEN the owner saves THE SYSTEM SHALL append a version snapshot and guard unsaved changes.
- [ ] WHEN all children are Done THE v1 rows SHALL be cut over to v2 in one shot via the deploy
      command (`--apply --verify`, idempotent, PT + translations, strict writes, temporary read
      fail-safe), every old-pipeline published row rebuilt as a draft, and the dead v1 files +
      `blog_image_map` removed with a no-regression guard, evidenced in Test Evidence.

## Gherkin Scenarios

```gherkin
Feature: Blog post owns structure, voice and images

  Scenario: Carousel-origin generation always drafts
    Given a public carousel
    When the owner creates a blog post from it
    Then a draft post exists with generated sections and images
    And the post is not published

  Scenario: Public blog renders the post's own images
    Given a drafted v2 blog post with a cover and section images
    When an anonymous visitor opens /blog/{id} after publish
    Then each section shows its own image with a non-empty alt
    And no image src contains /slide-images/

  Scenario: Voice gate
    Given a persona with writing samples
    When the writer drafts the article
    Then the stored voice score is at least 70 or exactly one rewrite pass ran

  Scenario: Language buttons switch the content
    Given a post with PT and EN documents
    When the owner clicks EN in the editor
    Then the EN cover and sections are shown and editable
    And the PT document is unchanged

  Scenario: Review and schedule
    Given an approved post
    When the owner schedules a future publication
    Then the post is published by the due-post sweep at that time
```

## Delta

### ADDED

- Epic tracking AE-0422..AE-0426 + AE-0428 (cleanup), ADR-0025, the architecture companion, and the
  ticket-owned backend + frontend `.feature` specs (plus the reconciled legacy specs).

### MODIFIED

- Blog public rendering, editor, AI contract, `blog_posts.content` (all via the children).

### REMOVED

- Carousel slide injection into blog bodies (AE-0422); positional `blog_image_map` mapping and the
  field itself and the dead blog-v1 components/hooks (AE-0428); the carousel→blog dual-write
  (AE-0422, so it cannot clobber v2).

## Affected Areas

- Backend: blog domain/application/agents, image generation, cutover command, generation worker
- Frontend: public blog, blog editor, publishing module
- Database: `blog_posts.content` data cutover (no schema change)
- API: two generation routes + image/rewrite routes; suggest contract tightened
- Tests: backend + frontend features/units
- Docs: ADR-0025, architecture companion, prompt README
- Prompts/LLM: new `blog/v1` writer + image-prompt templates
- Observability: Langfuse `blog_generation` / `blog_section_image`
- Deployment: explicit one-shot cutover in `deploy.yml` between Postgres-up and full-stack-up; no
  Alembic dependency (the separate AE-0207 head/stamp reconcile still gates schema migrations)

## Dependencies

- Blocks: none.
- Blocked by: none.
- Related: ADR-0003, ADR-0006, ADR-0009, ADR-0011, ADR-0013, ADR-0014, ADR-0016, AE-0296, AE-0347,
  AE-0411, AE-0416.

## Implementation Plan

1. A (AE-0422) ships first and alone.
2. B (AE-0423) before C and D.
3. C (AE-0424) and D (AE-0425) in parallel.
4. E (AE-0426) after D.
5. F (AE-0428) after C (the new image controls replace `ImageGenModal`) and A/B (the v2 read path
   exists); it may run before or after E, since E uses the v2 pipeline.

## QA Checklist

- [ ] Security reviewed
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-10-18 16:30

Epic created from the AE-0422 plan; ADR-0025 and the architecture companion written.

## Files Touched

Pending (per child).

## Test Evidence

Pending.

## QA Report

Pending.

## Decision Log

- **Make the post a document.** The root cause is the post being a view over carousel data; every
  symptom (voice, images, editing) follows from that.
- **Always draft for carousel-origin** (owner decision 1).
- **All images generated with gpt-image-2**, no carousel slides, no text in images (owner decision 2).
- **Hide then rebuild** the bad published rows (owner decision 3).
- **Review + scheduled publish are in scope** (owner revision); the endpoints already exist and get
  editor controls. `BLOG_ALLOW_SELF_REVIEW` keeps the single-author flow usable.
- **Image count = carousel `slide_count`** (owner revision); no `BLOG_IMAGE_MAX`.
- **PT/EN buttons switch content** in the editor and on the public page (owner revision).
- **Drop `blog_image_map` and the dead v1 files** (owner revision), with a no-regression guard.

## Blockers

None.

## Final Summary

Pending.
