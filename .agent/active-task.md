# Active Task

No active task. AE-0566 msgpack repair and external QA are complete; the overall audit remains blocked by the separate dnspython advisory.

## Rules

- Only one ticket should be active per agent session unless explicitly coordinating multiple tickets.
- The active ticket must exist under `.agent/tasks/`.
- Agents must update the active ticket before and after implementation work.
- QA must clear active task ownership after writing its report.
