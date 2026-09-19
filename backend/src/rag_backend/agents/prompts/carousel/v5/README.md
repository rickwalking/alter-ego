# Carousel v5 prompts (AE-0347)

Prompt templates for the `hero_lower_third_v1` presentation contract. v5 supersedes
[v4](../v4/README.md) for the editorial content path; v4 is kept for rollback.

## What changed from v4

- **`long_form_notes` is now part of the return contract.** Since AE-0032 the
  public blog is composed from each slide's `long_form_notes`, but neither v3 nor
  v4 ever asked the model for them, so every carousel blog was an H1-only stub.
  `content.yaml` now requires 2-4 paragraphs of long-form prose per slide.
- `outline.yaml` is an unchanged copy of v4 (still not wired; the outline agent
  renders `version=v3`).

## Files

- `content.yaml` — per-slide draft generation with cross-slide distinctness and
  mandatory `long_form_notes`. **This is the only v5 template wired in**
  (`ContentDraftAgent` renders `carousel/content` at `version=v5`).
- `outline.yaml` — forward-compat copy, not yet wired.

See the v4 README for the policy fragment and usage; only the `version` changes.
