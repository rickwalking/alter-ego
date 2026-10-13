# Active Task

AE-0351 is Dev Complete on `feat/ae-0351-autopilot-service-api-key-auth`.

Scoped service API key for `/api/autopilot/*`.

## Rules

- Only one ticket should be active per agent session unless explicitly coordinating multiple tickets.
- The active ticket must exist under `.agent/tasks/`.
- Agents must update the active ticket before and after implementation work.
- QA must clear active task ownership after writing its report.
