# Active Task

AE-0360 is Dev Complete on `feat/ae-0360-grokbot-scout-ops-cursor-cli`.

Grok Bot scout intake: `POST /api/autopilot/x-signals` and `POST /api/autopilot/scout-failed`, plus the owner routine pack.

## Rules

- Only one ticket should be active per agent session unless explicitly coordinating multiple tickets.
- The active ticket must exist under `.agent/tasks/`.
- Agents must update the active ticket before and after implementation work.
- QA must clear active task ownership after writing its report.
