# GrokBot Scout

The daily scout runs as a Cursor Grok Bot routine. The droplet does not install the Cursor CLI, does not store a Cursor API key, and does not run a systemd timer. Grok Bot authenticates with the owner's Cursor account and uses the existing Grok Bot plan limits.

The bot holds only the scoped autopilot key. That key cannot publish and cannot call routes outside `/api/autopilot/*`.

## Versioning

`v3/` is the current routine pack (AE-0377). It adds `mode` (`news_analysis` = Radar IA, at most one per São Paulo week; `pov` = Ponto de Vista) and, for `pov`, a `thesis_draft` the owner confirms, edits or discards on Telegram before generation, plus the scout's `pov_format` (`opiniao`, `como_eu_faco`, `erros_e_mitos`, `comparacao`) and `slide_count` (8–10); both default to `opiniao` / 9 when omitted. Topics rank by debate potential ("o que isso muda para devs brasileiros"), and `flat_editorial` is the default image style.

`v2/` is the previous routine pack and still accepted (a topic without `mode` is Radar IA) (AE-0361). It adds the carousel rules: audience and niche in 1 to 3 words, a brief that names the title's theme, an `image_style` picked from a decision table (`neo_anime` by default), and `image_guidance` with a theme-specific background.

`v1/` is **superseded** and must not be run. From AE-0361 on, v2 is required: the v1 example brief does not name its title's theme, so the backend rejects it with `brief_off_theme`. The owner must paste `v2/routine.md`. `v1/` is immutable and kept for history. Never edit files under `v1/`, `v2/` or `v3/` (v3 got `pov_format` / `slide_count` in the AE-0371 PR #106 review, before its first release; it is frozen from that release on). To change the routine, copy the latest directory to the next version (`v4/`) and change the copy.

## Owner setup

1. Create a Bot named "GrokBot Scout" in the Grok Bot app.
2. Log in to x.com in the Bot browser via takeover.
3. Create `/workspace/grokbot/config` through the Bot command line. Type `ALTER_EGO_URL` and `GROKBOT_API_KEY` via takeover so the key never enters the chat transcript. The file is shell assignments, for example `ALTER_EGO_URL=https://your-host` and `GROKBOT_API_KEY=` followed by the scoped key.
4. Paste `v3/routine.md` and ask the Bot to create the routine "every day at 08:00 America/Sao_Paulo".
5. Do one test run. The chat should show the `/api/autopilot/topics` response and must not show the API key.

## What the bot may call

- `GET /api/autopilot/signals`
- `POST /api/autopilot/x-signals`
- `POST /api/autopilot/topics`
- `POST /api/autopilot/scout-failed`

`x-signals` returns `accepted` as the canonical `https://x.com/.../status/...` URLs that topic intake will allow for the next 6 hours. A profile URL or a status older than 48 hours is listed under `rejected` and is not stored. The rest of the batch is still accepted.

## Carousel defaults

The backend creates every GrokBot carousel with the OpenAI image model and the `auto` palette theme. The bot picks only the image style and writes the image guidance. A topic that breaks a carousel rule is listed under `rejected` with `image_style_unsupported`, `audience_not_simple`, `niche_not_simple`, `brief_not_simple` (brief over 600 characters) or `brief_off_theme`; the rest of the batch is still accepted. Only a malformed field (for example an `image_style` over 40 characters or a brief over 800) rejects the whole batch with 422. See `docs/architecture/grokbot-autopilot.md` §5.3.

## Known issue

Routines may start late or miss runs (Cursor forum, September 2026). The backend daily cap and idempotency make re-runs safe: posting the same status URL again updates that signal, and posting the same topic again does not queue a second run.
