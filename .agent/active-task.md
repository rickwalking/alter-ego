# Active Task

AE-0359 is In Development on `feat/ae-0359-autopilot-prod-wiring`.

Prod wiring is committed. Not moved to Dev Complete: `gate-capture.sh all` fails only on the pre-existing `frontend:security` npm audit.

## Rules

- Only one ticket should be active per agent session unless explicitly coordinating multiple tickets.
- The active ticket must exist under `.agent/tasks/`.
- Agents must update the active ticket before and after implementation work.
- QA must clear active task ownership after writing its report.
