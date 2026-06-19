---
name: carousel-refinement
description: Refine existing carousel content — copy, images, or design. Use when the user asks to tweak, rewrite, shorten, regenerate, or change visual properties of an already-created carousel. Never use for creating a new carousel from scratch.
version: 1.0.0
---

# Carousel Refinement

## Purpose

Modify existing carousel projects without triggering a full re-generation.
Refinement is faster and cheaper than creating from scratch because it
reuses the research and content already produced.

## Tools

### refine_carousel_copy

Rewrite text on a carousel project.

**Targets:**
- `instagram_caption` — the Instagram caption
- `linkedin_post_pt` — Portuguese LinkedIn post
- `linkedin_post_en` — English LinkedIn post
- `slide_heading:N` — heading of slide N (default language: pt)
- `slide_heading:N:pt` — heading of slide N in Portuguese
- `slide_heading:N:en` — heading of slide N in English
- `slide_body:N` — body of slide N (default language: pt)
- `slide_body:N:pt` — body of slide N in Portuguese
- `slide_body:N:en` — body of slide N in English

**Behavior:**
- Rewrites the target text with the given instruction
- Persists the change to the database
- Automatically re-exports slide JPGs and PDF for the touched language
- Does NOT regenerate images or redesign the carousel

### regenerate_slide_image

Regenerate the hero image for a specific slide.

**Parameters:**
- `slide_number` — which slide (1-indexed)
- `instruction` — natural-language description of the desired change

**Behavior:**
- Rewrites the image prompt based on the instruction
- Calls the image generation API
- Re-exports the slides automatically

### refine_carousel_design

Apply CSS overrides to the carousel visual design.

**Parameters:**
- `instruction` — natural-language description (e.g., "make images bigger",
  "increase font size", "add more padding")

**Behavior:**
- Generates CSS overrides from the instruction
- Writes them to `design_overrides.css` in the project output directory
- Re-renders the HTML and re-exports JPGs + PDFs
- Does NOT regenerate images or rewrite copy

## Critical Rules

- Always extract the `project_id` from the UI prefix `(carousel project_id=<uuid>)`
- For slide-text edits, specify the language suffix (`:pt` or `:en`) when the
  user mentions a specific language; omit the suffix for the primary (pt) text
- Do NOT use refinement tools for creating a new carousel — use the carousel
  pipeline subagent instead
