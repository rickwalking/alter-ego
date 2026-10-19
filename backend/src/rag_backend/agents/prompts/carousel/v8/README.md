# Carousel v8 prompts (AE-0430)

Only `slide_translations.yaml` moves to v8; every other carousel prompt keeps its
version (the content drafter stays on v6, the caption on v7). v6
`slide_translations.yaml` is kept for rollback.

## What changed from v6

- **Structured fields are translated.** Prod carousel `5344b6c6`: the PT intro had a
  TL;DR strip, the translator only sent and returned `heading`/`body`, so the EN intro
  came back without one and the content gate blocked on `translation_shape_mismatch`
  (`intro:tldr` vs `intro:plain`), which the owner could not fix by hand. The request
  now carries `tldr_strip` and the `features` / `summary_points` / `actions` texts,
  and the prompt asks for the same fields back with the same shape.
- **Length.** Each EN text is asked to stay about as long as its PT source or shorter
  (the EN copy overflowed its budgets most often on that carousel).

The parser does not trust the answer's shape: an item list with a different item
count, or a missing TL;DR, falls back to the PT value, and the content-gate field
repair (`carousel_gate_repair/v1/field_repair.yaml`) translates it.
