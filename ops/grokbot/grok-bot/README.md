# GrokBot Scout

The daily scout runs as a Cursor Grok Bot routine. The droplet does not install the Cursor CLI, does not store a Cursor API key, and does not run a systemd timer. Grok Bot authenticates with the owner's Cursor account and uses the existing Grok Bot plan limits.

The bot holds only the scoped autopilot key. That key cannot publish and cannot call routes outside `/api/autopilot/*`.

## Versioning

`v1/` is immutable. Never edit files under `v1/`. Copy the directory to `v2/` and change the copy.

## Owner setup

1. Create a Bot named "GrokBot Scout" in the Grok Bot app.
2. Log in to x.com in the Bot browser via takeover.
3. Create `/workspace/grokbot/config` through the Bot command line. Type `ALTER_EGO_URL` and `GROKBOT_API_KEY` via takeover so the key never enters the chat transcript. The file is shell assignments, for example `ALTER_EGO_URL=https://your-host` and `GROKBOT_API_KEY=` followed by the scoped key.
4. Paste `v1/routine.md` and ask the Bot to create the routine "every day at 08:00 America/Sao_Paulo".
5. Do one test run. The chat should show the `/api/autopilot/topics` response and must not show the API key.

## What the bot may call

- `GET /api/autopilot/signals`
- `POST /api/autopilot/x-signals`
- `POST /api/autopilot/topics`
- `POST /api/autopilot/scout-failed`

`x-signals` returns `accepted` as the canonical `https://x.com/.../status/...` URLs that topic intake will allow for the next 6 hours. A profile URL or a status older than 48 hours is listed under `rejected` and is not stored. The rest of the batch is still accepted.

## Known issue

Routines may start late or miss runs (Cursor forum, September 2026). The backend daily cap and idempotency make re-runs safe: posting the same status URL again updates that signal, and posting the same topic again does not queue a second run.
