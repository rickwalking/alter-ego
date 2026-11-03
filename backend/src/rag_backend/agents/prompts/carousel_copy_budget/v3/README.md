# carousel_copy_budget, v3

Only `fit_fields.yaml` has a v3; it renders from `COPY_BUDGET_PROMPT_VERSION`.
`slide_limits.yaml` stays at v2. v1 `fit_fields.yaml` is kept for rollback.

Changes from `v1/fit_fields.yaml` (AE-0607, prod fit timeouts of 2026-11-03):

- `max_tokens` 4096 → 32000. The template text is unchanged.
- Measured in Langfuse on the first prod attempt (6 fields, ~2.8k input
  tokens): every call spent exactly 4096 tokens on reasoning and returned
  empty content. That was 3 × `deepseek-v4.1-flash` (34.9 s, 37.8 s, 37.8 s)
  and then the fallback `qwen3.8-flash` (63.3 s), 173.9 s in all, before the
  step's 180 s deadline. The bound value is what the provider gets:
  langchain-openai sends it as `max_completion_tokens` in place of the model's
  32000 default.
- 32000 is what the drafting and the content-gate repair already run with on
  this endpoint. At the measured ~117 reasoning tok/s, the step's 180 s fits
  ~21k tokens, so the deadline, not the cap, is now the outer bound.
