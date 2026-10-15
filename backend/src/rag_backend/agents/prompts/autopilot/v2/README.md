# `autopilot/` prompt domain, v2

Loaded via `render_prompt("autopilot", "<name>", variables, version="v2")`.

## v2 (AE-0392)

- `revise_feedback.yaml`: same sentence as v1, plus:
  - `Measured` is always filled (the runner reports the forbidden phrases, the
    `rule@slide` pairs of a content-quality failure, or the measured counts).
  - optional `violations` list: one line per failing slide (slide, locale,
    field, rule id, offending text). The revise is told to change only those
    slides.
  - Variables: `phase`, `reason`, `detail`, `violations` (list of strings,
    may be empty).

v1 is kept for rollback.
