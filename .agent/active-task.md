# Active Task

AE-0355 is Dev Complete on `feat/ae-0355-autopilot-telegram-notifier`.

Telegram owner notices for autopilot runs: album, keyboard, status, reminder.

## Rules

- Only one ticket should be active per agent session unless explicitly coordinating multiple tickets.
- The active ticket must exist under `.agent/tasks/`.
- Agents must update the active ticket before and after implementation work.
- QA must clear active task ownership after writing its report.
