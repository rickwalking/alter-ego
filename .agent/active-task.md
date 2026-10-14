# Active Task

AE-0359 is Dev Complete on `feat/ae-0359-autopilot-prod-wiring`.

`gate-capture.sh all` is green (fail 0). `frontend:security` passes. Four backend database gates skipped because `DATABASE_URL` is unset.

## Rules

- Only one ticket should be active per agent session unless explicitly coordinating multiple tickets.
- The active ticket must exist under `.agent/tasks/`.
- Agents must update the active ticket before and after implementation work.
- QA must clear active task ownership after writing its report.
