# carousel_copy_budget, v3

Only `fit_fields.yaml` has a v3; it renders from `COPY_BUDGET_PROMPT_VERSION`.
`slide_limits.yaml` stays at v2. v1 `fit_fields.yaml` is kept for rollback.

Changes from `v1/fit_fields.yaml` (AE-0607, prod fit timeouts of 2026-11-03):

- `max_tokens` 4096 → 32000. The template text is unchanged. The fast model
  (`deepseek-v4.1-flash`) spends most of its output on reasoning (~2k tokens
  for a single-slide JSON in the routing benchmarks), so a 6-7 field shorten
  task can use the whole 4096 cap before it writes the answer; an empty answer
  is re-rolled on the same model before the queue moves to its fallback. The
  content-gate field repair, which gets the same field shape on the same
  queue, runs at the model default of 32000 and answered in prod right after
  both fit timeouts.
