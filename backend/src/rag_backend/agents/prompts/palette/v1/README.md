# Palette prompts v1

Loaded through `agents.prompts.registry`.

- `generate.yaml` — "create a palette with AI" in the New palette modal: the owner's
  description (sanitised, delimited as data) → JSON `{"candidates": [...]}` with three
  palettes. Fast model queue. The server re-validates every candidate and repairs the
  contrast to WCAG AA, so the prompt's contrast rule is a hint, not the guarantee.
