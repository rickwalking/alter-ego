# `owner_retry/` prompt domain, v1

Loaded via `render_prompt("owner_retry", "<name>", variables, version="v1")`.

## v1 (AE-0606)

- `retry_feedback.yaml`: the fixed, system-written feedback line an owner Retry
  sends when it revises a phase (a blocked gate, a failed phase with its gate
  open, or a carousel the system rejected). It names the reason (the
  escalation reason, the engine's approve blocker, `phase_failed` or
  `carousel_rejected`) and, when known, the persona score and its threshold.
  - Variables: `phase`, `reason`, `detail` (may be empty).
