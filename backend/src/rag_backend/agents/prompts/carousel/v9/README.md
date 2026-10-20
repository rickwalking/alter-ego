# Carousel v9 prompts (AE-0436)

Only `slide_translations.yaml` moves to v9; every other carousel prompt keeps its
version. v8 `slide_translations.yaml` is kept for rollback.

## What changed from v8

- **Emphasis convention.** Prod carousel `7acaf967` (F-09): the EN columns kept
  PT-style `**…**` emphasis, which the content gate did not flag. The request now
  sends PT emphasis already converted to `<strong>…</strong>`, and the prompt
  states the EN rule explicitly: `<strong>` only, never `**`.
- **No label scaffolding.** The prompt tells the model never to write locale
  markers or field labels into any translated text (prod `7acaf967` shipped
  "**CTA creator: radar IA.**" in the EN body, F-04).

The parser does not trust the answer's shape: an item list with a different item
count, or a missing TL;DR, falls back to the PT value, and the content-gate field
repair (`carousel_gate_repair/v1/field_repair.yaml`) translates it. Any emphasis
mismatch that survives is a blocking `emphasis_markup_locale_mismatch` violation
normalized deterministically at write time.
