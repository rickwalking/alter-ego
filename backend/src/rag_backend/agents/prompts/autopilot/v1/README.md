# `autopilot/` prompt domain

Templates for the in-process autopilot runner (AE-0354). Loaded via
`render_prompt("autopilot", "<name>", variables, version="v1")`.

## v1

- `revise_feedback.yaml` — text passed to `resume(revise)` when a
  deterministic gate check fails. Variables: `phase`, `reason`, `detail`.
