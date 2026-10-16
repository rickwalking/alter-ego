# GrokBot Autopilot — Architecture

> Status: **proposed** (see [ADR-0020](../decisions/0020-grokbot-autopilot.md)) · Date: 2026-10-13 · Tier: **T3 epic**

GrokBot finds viral AI themes, builds a carousel through the existing editorial
workflow, sends it to Pedro on Telegram for **Approve / Rework / Reject**, and
publishes it to Instagram **only after an explicit human approval**.

Constraint: **no new subscriptions.** The design uses only:

- the existing Cursor/Grok plan for the scouting LLM,
- the existing droplet,
- free APIs: Telegram Bot API, Instagram Graph API, HN Algolia, Hugging Face, RSS, Bluesky.

Per-carousel spend on the providers already configured (image generation, LLM
calls) still applies. A daily cap bounds it.

---

## 1. Design principles (the "no mistakes" rules)

1. **The LLM proposes; code decides; the human publishes.** Grok (Cursor CLI) does one job: rank pre-fetched signals and return topic JSON.
   - Grok never holds API credentials.
   - Grok never calls the alter-ego API.
   - Grok can never trigger a publish.
   - Publishing can only be triggered by a Telegram callback from Pedro's allowlisted `chat_id`.
2. **All scraped content is untrusted.** HN titles or Bluesky posts can carry prompt injection.
   - The scout runs read-only: no `--force`, sandbox enabled, no MCP, no secrets in its environment.
   - Its output is schema-validated before anything uses it.
3. **Autopilot runs inside the backend, not over HTTP.** It drives the existing `EditorialWorkflowService` from the worker loop. This avoids four problems:
   - 6× `resume` calls with `lock_version` races,
   - a 60-min JWT with no refresh,
   - the ~100 s Cloudflare cap on the synchronous `workflow/start`,
   - in-process SSE that is invisible to outside processes.
4. **Every state transition is idempotent and conditional:** `UPDATE … WHERE state = <expected>`.
   - A double-tapped Telegram button must never double-post to Instagram.
   - Telegram retries webhooks, so `update_id` is de-duplicated.
5. **Nothing becomes public before approval.** Telegram previews upload the JPEGs straight from disk as multipart.
   - `is_public` (the `/publish` release) is set only on approval.
   - Instagram's fetcher needs that flag.
6. **Fail loud, never stuck.** Every failure path does two things:
   - ends in a Telegram message,
   - ends in a terminal state with a reason.

   The existing 72 h auto-reject stays as the backstop.

---

## 2. Component view

```
 DROPLET HOST (systemd)                       BACKEND CONTAINER (FastAPI, existing)
 ┌──────────────────────────────┐            ┌───────────────────────────────────────────┐
 │ grokbot-scout.timer (daily)  │            │ modules/autopilot  (NEW bounded context)  │
 │  1. GET /api/autopilot/      │──API key──▶│  • signals collector (HN, HF, RSS, Bsky)  │
 │     signals   (JSON bundle)  │            │  • topic intake  POST /autopilot/topics   │
 │  2. timeout 600 agent -p     │            │  • dedupe + daily cap + policy            │
 │     --model grok-4.7-high    │            │  • AutopilotRunner (worker-loop tick)     │
 │     --output-format json     │            │      drives EditorialWorkflowService:     │
 │     (read-only, sandboxed)   │            │      start → auto-approve gates → stop at │
 │  3. validate JSON schema     │            │      final_review                         │
 │  4. POST /api/autopilot/     │──API key──▶│  • TelegramNotifier (sendMediaGroup +     │
 │     topics                   │            │      inline keyboard)                     │
 └──────────────────────────────┘            │  • POST /api/telegram/webhook (secret hdr)│
                                             │  • InstagramPublishJob (outbox, idempot.) │
         Telegram (Pedro) ◀──────────────────│  • IG token refresher (every ~50 days)    │
              │  Approve / Rework / Reject   └──────────────┬────────────────────────────┘
              └──────────── webhook ───────────────────────▶│ existing: editorial workflow,
                                                            │ MetaInstagramPublisher, persona,
                                       Instagram Graph API ◀┘ slide-images route (public JPEG)
```

**Why the scout runs on the host, not in the container.**

- `agent` (Cursor CLI) needs its own login/API key and install. Keeping it outside the app image avoids bloating the image and keeps the Cursor key separate from the backend.
- `deploy.yml` rewrites the server `.env` on every deploy. The scout's secrets must live elsewhere: `/etc/grokbot/env`, mode 600, owned by user `grokbot`.

---

## 3. End-to-end flow

```
[timer 08:00] scout → GET signals → Grok ranks → POST topics (≤3 candidates)
   backend: dedupe vs last 60 days of carousels → pick top-1 (cap: N/day) → AutopilotRun(state=queued)
[worker tick] queued → create CarouselProject + workflow start (in-process, no HTTP cap)
   loop per gate (research, outline, content, design, images):
       awaiting_human & checks pass  → approve(expected_version=lock_version)
       content persona score < 70    → (only when scored) revise("raise voice match: …") up to 2× → else ESCALATE
       presentation_validation_block → revise up to 1× → else ESCALATE
       phase failed / run stale      → ESCALATE
       parked (no run in flight, checkpoint neither awaiting nor failed)
                                     → wait 10 min, then re-drive once (approved/in_progress)
                                       or ESCALATE engine_parked_no_run_in_flight
   final_review awaiting_human → state=awaiting_owner → Telegram:
       sendMediaGroup(slides 1-10, PT) + caption preview + score summary
       sendMessage(caption preview + up to 5 quality-issue lines,
                   inline keyboard: ✅ Approve · ✏️ Rework · 🗑 Reject [· 🛠 Fix issues])
[Pedro taps]
   Approve → keyboard: 🚀 Publicar agora · 🗓 Agendar   (AE-0370, see §5.5)
   Publicar agora → resume approve(final_review) → approved_for_publish
           → release (is_public=true) → InstagramPublishJob(queued)
   Agendar → slot or typed time → approve(final_review), no release → state=scheduled
           → due tick: release → InstagramPublishJob
   Rework  → keyboard: Text | Design | Images | Outline → ForceReply "what to change?"
           → webhook queues phase + feedback (state=reworking) and answers at once
           → worker runner: resume revise(structured_feedback.target_phase, feedback)
           → runner re-drives gates → back to Telegram (revision cap 5/phase, existing)
   Reject  → state=rejected (no publish, project stays private)
   Fix issues (AE-0367; shown only when something is fixable)
           → webhook: clean carousel → "Nothing to fix"; else CAS → reworking
             (reason owner_autofix), queue the fix, old keyboard → "Superseded by fixed version"
           → worker runner: deterministic repair of the slide rows + checkpoint copy
             (sentence case, proper nouns from the carousel vocabulary, features/summary
             points from the outline, <strong> balancing), one bounded LLM re-translate
             of untranslated EN fields only, lock-version CAS, republish (hero images kept)
           → final-review stop → awaiting_owner + fresh review (remaining issues listed)
[publish job] check content_publishing_limit → create item containers → CAROUSEL container
   → poll status → media_publish → persist ig_post_id + permalink → Telegram "✅ posted <link>"
   any error → retry w/ backoff (3×) → Telegram "❌ publish failed: <reason>" + [Retry] button
```

**How a gate decision runs (AE-0363).** Approve, revise, and re-drive go through the
editorial facade operation `run_automation_phase`, the same run-owned path as the HTTP
`POST /workflow/resume`. The tick session only does the pre-run steps (in-flight guard,
revision-cap check, `lock_version` CAS, flip to `in_progress`, which stamps
`run_started_at`/`run_heartbeat_at`) and **commits them before any LLM work**. The phase then
runs inline through `execute_resume_run`: epoch fence, 60 s heartbeat loop, `run.started` /
`run.finished`, its own DB session, and a failure marks the row `failed` (the next tick
escalates it with a Telegram notice). Inline (not fire-and-forget) keeps one run per tick and
lets the driver map refusals (`version_conflict`, `revision_cap`, `in_progress`) at once. A
re-drive re-runs the pending node with `ainvoke(None)`: a `Command(resume=…)` there would be a
null resume that the next gate's `interrupt()` consumes, approving it unreviewed. Ops recovery
for a parked carousel: `backend/scripts/redrive_parked_carousel.py` (dry run by default).

**Reminders.** `awaiting_owner` triggers a Telegram nudge at 24 h. After 72 h the runner
moves the run to `expired` and posts a Telegram notice; the existing 72 h stuck
auto-reject still closes the carousel.

**QA round 1 hardening (AE-0348).** Every autopilot worker step commits or rolls back on its
own, so a failing step never rolls back the reaper or the auto-reject. An engine error the
runner cannot classify ends the run (`escalated`, or `failed` from `queued`) with an
`engine_error:` reason instead of retrying forever. An `escalated` run whose carousel is
back at final review at a new lock version returns to `awaiting_owner`. The manual
Instagram route publishes an autopilot carousel only through its `publishing` run, and
both callers take a compare-and-set publish claim first.

**QA round 2 hardening (AE-0348).**
- Escalations are closed, not left open. An `escalated` run becomes `rejected` (and the owner
  is told on Telegram) when its carousel is rejected in the web UI or by the stuck
  auto-reject, or after 72 h with no fix. The wake scan rotates by `wake_checked_at`, so old
  escalations never starve a newer one.
- A `PUBLISHED` container's media is matched only to the single album posted after the stored
  container creation time. With no match or an ambiguous match, the run ends `publish_failed`
  with `instagram_published_media_unknown`. That reason never offers or accepts Retry, and
  the owner is told the post may already be live.
- Every Graph request has an overall deadline. The publish-claim stale window is derived from
  the worst-case publish time, and a stale claim is never taken over while a container
  younger than 24 h has no post id. A container older than 24 h is first checked for
  `PUBLISHED` and recovered instead of being posted again.
- The manual publish of a carousel without a run stores its container id in
  `instagram_manual_publishes` before `media_publish`, so a retry resumes that container.
- A run that is `publishing` but whose carousel is not public yet (the approve release is
  still landing) is not failed during a 5-minute grace window.
- The Telegram notifier re-reads the 10 minutes behind its outbox cursor. Outbox
  `created_at` is the transaction start time, so a long transaction can commit an event
  behind the cursor; the notice ledger dedupes the re-read events.

**QA round 3 hardening (AE-0348).**
- The notifier reads the re-scan window and the events after its cursor as two queries, each
  with its own limit, so a window full of settled notices never stalls new ones.
- A run held in `publishing` by a dead worker's container (stale claim, container under 24 h,
  no post id) is not left for 24 h. The job reads the container status once per tick:
  `PUBLISHED` is recovered, `FINISHED` gets one `media_publish` under the claim, `ERROR` /
  `EXPIRED` fail the run, `IN_PROGRESS` waits. A hold over 30 minutes is told to the owner once.
- The escalation sweep runs the wake check before closing. A carousel back at final review at a
  new lock version is never closed. Without a notifier such a run is first recorded as
  `notifier_unconfigured` (restarting its 72 h) and only then may close.
- The manual publish re-reads its ledger row after taking the claim.
- The research fetch has one 15 s deadline over all hops, reads only `text/html`,
  `application/xhtml+xml` and `text/plain` (anything else skips the source), sends browser
  headers, decodes by header / `<meta>` charset, strips resource-hint `<link>` tags and
  launches Chromium with `--dns-prefetch-disable`. Pages that need JavaScript come back as
  their static HTML.

---

## 4. Autopilot state machine (new table `autopilot_runs`)

| State | Next | Trigger |
|---|---|---|
| `queued` | `generating` / `awaiting_thesis` / `failed` | runner tick picks it up / the topic is POV and no thesis is confirmed yet (AE-0377) / workflow start failed 3× (provider 429/503) |
| `awaiting_thesis` | `queued` / `rejected` / `expired` | owner confirms or edits the thesis / owner discards the topic / 72 h (AE-0377) |
| `generating` | `awaiting_owner` / `escalated` / `failed` | gates auto-approved to final_review / check failed after retries / workflow failed |
| `awaiting_owner` | `publishing` / `scheduled` / `reworking` / `rejected` / `expired` | Publicar agora / Agendar (AE-0370) / Rework / Reject / 72 h |
| `scheduled` | `publishing` / `awaiting_owner` / `expired` / `scheduled` | `scheduled_at` is due, or Publicar agora / Cancelar agendamento / the carousel is no longer approved at the due time / Mudar dia/horário (AE-0404: a new `scheduled_at`) |
| `reworking` | `awaiting_owner` / `escalated` | revise drove back to final_review / cap hit |
| `escalated` | `awaiting_owner` / `rejected` | Pedro fixes it in the web UI / the carousel is rejected (web UI or stuck auto-reject), or 72 h pass with no fix |
| `publishing` | `published` / `publish_failed` / `awaiting_owner` | IG success / 3 retries exhausted / the editorial approve refused the owner's Approve (review stays open) |
| `publish_failed` | `publishing` | Pedro taps [Retry] |

Columns:

- `id`, `carousel_project_id` (FK, unique), `topic_candidate_id`, `state`
- `state_reason`, `attempts` (publish attempts; reset on every entry to `publishing`), `start_attempts`
- `rework_phase`, `rework_feedback` (the owner's queued rework), `escalated_version`, `publish_claimed_at`, `wake_checked_at` (escalated wake-scan rotation)
- `telegram_message_ids` (JSONB)
- `ig_container_id`, `ig_post_id`, `ig_permalink`
- `scheduled_at` (AE-0370: the owner's publish time; index `(state, scheduled_at)`)
- `created_at`, `updated_at`

Every transition is one conditional UPDATE, and it emits `content.autopilot.*` through the
existing transactional outbox (ADR-0004). **`ig_post_id IS NOT NULL` makes publish a no-op.**
That is the idempotency key.

Supporting tables:

- `topic_candidates`: `id`, `title`, `angle`, `audience`, `niche`, `brief`, `sources[]`, `score`, `signal_hash`, `status`, `created_at`.
  - Unique on `signal_hash` for dedupe.
- `integration_credentials`: `provider`, `encrypted_token`, `expires_at`, `refreshed_at`. Holds the IG long-lived token.
- `telegram_updates`: `update_id` PK. Used for webhook dedupe and pruned after 7 days.

---

## 5. The scout (Cursor CLI + Grok)

```bash
# /usr/local/bin/grokbot-scout  (run by grokbot-scout.service, user grokbot)
set -euo pipefail
WORK=$(mktemp -d); trap 'rm -rf "$WORK"' EXIT
curl -fsS -H "X-Api-Key: $GROKBOT_API_KEY" "$ALTER_EGO_URL/api/autopilot/signals" > "$WORK/signals.json"
cp /opt/grokbot/scout_prompt.md /opt/grokbot/topics.schema.json "$WORK/"
cd "$WORK"
env -i HOME="$HOME" PATH="$PATH" CURSOR_API_KEY="$CURSOR_API_KEY" \
  timeout 600 agent -p --trust --sandbox enabled \
    --model "${GROKBOT_MODEL:-grok-4.7-high}" --output-format json \
    "$(cat scout_prompt.md)" > result.json
jq -er '.result' result.json | python3 /opt/grokbot/validate_topics.py > topics.json   # strips fences, validates schema
curl -fsS -X POST -H "X-Api-Key: $GROKBOT_API_KEY" -H 'Content-Type: application/json' \
  --data @topics.json "$ALTER_EGO_URL/api/autopilot/topics"
```

- **Model id.** "Grok 4.7 high" is `--model grok-4.7-high`; the effort level is part of the id. Run `agent --list-models` once to confirm it. `GROKBOT_MODEL=grok-4.6-high` is the fallback, because 4.7 has had `not_found` reports in automations.
- **Secrets.** `env -i` means the agent process sees **no** `GROKBOT_API_KEY`. Only the shell wrapper holds it.
- **Hangs.** `timeout 600` guards against the known `agent -p` hang.
- **Failure handling.** A non-zero exit triggers `OnFailure=grokbot-notify@%n.service`, which posts to Telegram through the backend: `POST /api/autopilot/scout-failed`, API key.
- **Systemd timer.** `OnCalendar=*-*-* 08:00 America/Sao_Paulo`, `Persistent=true`, `RandomizedDelaySec=10m`.
- **Prompt files.** Prompt and schema live as files, matching the project rule that prompts are never inline in code. The scout prompt is versioned at `/opt/grokbot/` from the repo `ops/grokbot/v1/`.

**Output contract** (`topics.schema.json`): 1–3 items, each with:

- `title`, `angle`, `why_viral`, `audience`, `niche`
- `brief` (≤ 800 chars)
- `sources[]`: URLs, which **must appear in signals.json**. The backend re-checks this, so the LLM cannot invent sources.
- `score` (0–100)

**Signal sources** (all free, collected **in the backend** so they are typed and tested):

| Source | Endpoint | Notes |
|---|---|---|
| Hacker News | `hn.algolia.com/api/v1/search?tags=story&query=AI&numericFilters=points>100,created_at_i>…` | 10k req/h, most reliable |
| Hugging Face | `huggingface.co/api/daily_papers` | upvotes + keywords |
| RSS | OpenAI / Anthropic / Google / Meta AI blogs, The Verge AI | stable |
| Bluesky | `app.bsky.unspecced.getTrends` (no auth) + `searchPosts` (free app password) | |
| GitHub | Search API `created:>D sort:stars topic:llm` (free token) | |
| **X via web search** | existing `ddgs` client (`application/services/tools/research_tool.py:26`), queries `site:x.com <keyword>` with `timelimit="d"` | post text + date + URL from search snippets; see §5.1 |

Excluded:

- **Reddit:** unauthenticated `.json` returns 403, and RSS reportedly ends 2026-11-13.
- **X official paths:** pay-per-use everywhere, including xAI `x_search`, the X API, and the Grok Bot X connector, which bills X dev credits. X data comes only through web search (§5.1).
- **Google Trends:** pytrends is dead.
- **Product Hunt:** non-commercial terms.

### 5.1 X signals via web search (and why not xcancel)

**Probe results (2026-10-13, from this machine):**

| Probe | Result |
|---|---|
| `xcancel.com/<user>`, `/search`, `/<user>/rss` | **HTTP 451, "XCancel service is suspended… due to a new development in the ongoing legal proceedings… until further notice."** |
| `nitter.net/<user>` | 200, but it is a JS bot-challenge page with no post content |
| `nitter.poast.org` | DNS no longer resolves |
| `ddgs.text("site:x.com AI agents viral")` | **Works.** It returned 8 `x.com/<user>/status/<id>` URLs with post text and dates in the snippets. |

**Decision:**

- X signals come from the **search-engine snippets**, the same `ddgs` path the carousel research pipeline already uses. The backend never requests x.com or any mirror. That is free, already proven in prod, and creates no legal/ToS exposure.
- The **xcancel URL rewrite is not built as a dependency.**
  - The service is down because of legal action (HTTP 451).
  - Nitter-style mirrors are being challenged or shut down.
  - Fetching X content through a mirror also sidesteps X's ToS.

**Collector `XWebSearchCollector`** (`modules/autopilot/infrastructure/collectors/x_web_search.py`):

1. Run each query template from `constants.py` (e.g. `site:x.com "AI agent"`, `site:x.com "new model" launch`, `site:x.com Claude OR GPT OR Gemini OR Grok`) with `timelimit="d"` and `max_results=10`.
2. Space queries 2–5 s apart. Use at most 6 queries per scout run, because DuckDuckGo throttles server IPs.
3. Keep only results whose URL matches `^https://(x|twitter)\.com/[A-Za-z0-9_]{1,15}/status/\d+$`. Canonicalise `twitter.com` to `x.com`.
4. Derive the post time from the snowflake id: `(id >> 22) + 1288834974657` ms. Drop anything older than 48 h. This is more reliable than the snippet date.
5. Emit `{source:"x_search", url, handle, text: snippet, posted_at}`. Cluster by keyword overlap. An item appearing across several queries or handles counts as the "virality" signal, because snippets carry no like or repost counts.
6. Results feed the same `signals.json`, and their URLs join the source allowlist that the topic intake checks.

**Optional and off by default: `XPostResolver` port.** It enriches a status URL with text and metrics through a configurable resolver (`AUTOPILOT_X_RESOLVER=none|mirror`, `AUTOPILOT_X_MIRROR_HOST=`).

- It rewrites `x.com/<handle>/status/<id>` → `https://<mirror_host>/<handle>/status/<id>`.
- A non-2xx response, or a body matching the existing `_is_block_page` heuristic (`agents/research_enrichment.py:109`), makes it fall back to the snippet silently.
- It is never on the critical path.
- Enabling it is the owner's explicit choice, with the ToS caveat above. Do not enable it while the mirror returns 451.

**Grok's role is unchanged.** The scout still has no network access of its own. Grok ranks what the backend collected. Letting `agent` browse would cost quota, add prompt-injection surface, and give non-reproducible results.

The official X route can still be added later if the new "X Subscription" pool turns out to include API/`x_search` credits.

---

### 5.2 Update 2026-10-14: the scout runs as a Cursor Grok Bot routine

This supersedes the host or Cursor CLI parts of §5, §2 and §7 (AE-0360).

**Why the change**
- Grok Bot is authenticated natively through the owner's Cursor account and uses the existing Grok Bot plan limits.
- So there is no Cursor API key, no droplet install and no systemd timer.
- Grok Bot routines run on a schedule in the cloud, on a persistent computer with a browser, command line and filesystem.

**What the routine does** (`ops/grokbot/grok-bot/v1/routine.md`, daily 08:00 America/Sao_Paulo)
1. Fetches `GET /api/autopilot/signals` with the scoped key.
2. Browses x.com **in its own logged-in browser** and collects at most 30 recent AI posts with likes, reposts and views.
3. Posts them to `POST /api/autopilot/x-signals`. The backend validates them (status regex, 48 h snowflake age) and adds them to the topic allowlist.
4. Ranks 1–3 topics.
5. Posts them to `POST /api/autopilot/topics`.
6. On failure, calls `POST /api/autopilot/scout-failed`, which sends a Telegram message.

**Trust model (unchanged)**
- The Bot holds only the scoped autopilot key. It is stored in `/workspace/grokbot/config` and typed by the owner via takeover.
- That key cannot publish or reach any other route.
- The backend still enforces schema, allowlist, dedupe and the daily cap.
- Publishing still requires the owner's Telegram approval.

**Kept**
- The `ddgs` X web-search collector (§5.1) stays as a backend signal source and fallback.

**Known issue**
- Grok Bot routines may start late or miss runs (Cursor forum, Sept 2026). Re-runs are safe because of the daily cap and dedupe.

### 5.3 Carousel defaults (AE-0361)

Every GrokBot carousel has a simple audience and niche, a brief on the selected theme, and image guidance. The routine pack is `ops/grokbot/grok-bot/v2/`.

**Fixed by the backend**
- `image_model` is always `openai` and the palette `theme` is always `auto`. The scout never sends either.
- The editorial driver creates the carousel with these values, the topic's `image_style`, and `custom_visual_details` = the image guidance.

**Chosen by the scout** (two optional fields on each topic)
- `image_style`: one of the OpenAI presets in `SUPPORTED_IMAGE_COMBOS`. The default is `neo_anime`. The API accepts any string of at most 40 characters; an unsupported value rejects only that topic with `image_style_unsupported`. The allowed set is derived from `SUPPORTED_IMAGE_COMBOS` (`SCOUT_IMAGE_STYLES`), so it cannot drift from the editorial presets.
- `image_guidance`: plain text, at most 400 characters, no URLs. It should end with `Background: <theme-specific scene>.`

| Theme of the topic | image_style |
|---|---|
| Default: AI agents, models, AGI, LLM launches, robotics/automation, cybersecurity, future of work, most AI themes | `neo_anime` |
| Data, benchmarks, how-to/tutorials, business strategy or ROI explainers | `flat_editorial` |
| Physical hardware launches: chips, GPUs, devices, consumer gadgets | `hyperreal` |
| Regulation, policy, ethics, society or real-world events involving people | `cinematic` |
| Humor, memes, hype or internet culture | `comic_neon` |

**Fallback guidance.** When the scout omits `image_guidance`, the runner builds it from constants in `modules/autopilot/carousel_constants.py`:
- For `neo_anime`: the Akira / Ghost in the Shell / Evangelion line.
- For any other style: a style-neutral line.
- Both end with `Background: <niche>-themed setting.`

Topics stored before AE-0361 get the same fallback.

**Simple-words rules.** Each failing topic is listed under `rejected`; the rest of the batch is still accepted.

| Rule | Reason |
|---|---|
| `image_style` is an OpenAI preset in `SUPPORTED_IMAGE_COMBOS` | `image_style_unsupported` |
| `audience` is 1–3 words | `audience_not_simple` |
| `niche` is 1–3 words | `niche_not_simple` |
| `brief` is at most 600 characters (the schema still allows 800 for v1 compatibility; 801+ is a 422) | `brief_not_simple` |
| `brief` shares at least one title word, case-insensitive, stop words ignored (`BRIEF_STOP_WORDS`) | `brief_off_theme` |

**Storage and review**
- `topic_candidates` gains `image_style` (NOT NULL, default `neo_anime`) and `image_guidance` (nullable). Revision `e7f8a9b0c1d2` is additive.
- The Telegram review message starts with `Audience: … · Niche: … · Style: …`, read from the carousel row.

### 5.4 Story after each post and the "add music" nudge (AE-0369)

After a carousel is posted, the autopilot also posts an Instagram Story announcing it, and tells the owner which music to add in the app (the Graph API cannot add music to a feed post).

**Story image.** `story_pt.jpg`, 1080x1920 JPEG (at most 8 MB), rendered with Pillow from the PT `slide_1.jpg`: the slide is centred on a blurred, darkened copy of itself, with a caption band reading `Novo post no perfil ↑`. Pillow's bundled font has no arrow glyph, so the arrow is drawn as a shape. The file lives in the serving root (the active artifact version, else the output dir) and is rendered again only when slide 1 is newer. Code: `modules/publishing/application/story_image.py`, behind the publishing facade (`prepare_story_image`, `story_image_file`, `build_public_story_image_url`).

**Public route.** `GET /api/carousels/{id}/story-image/pt.jpg`, `image/jpeg`. Same gate as `slide-images`: 404 unless the carousel is public, and 404 until the image is rendered.

**Story step.** `InstagramStoryStep` (`modules/autopilot/application/story_step.py`) runs inside `_mark_published`, after the post id is stored and before the `publishing → published` transition, under the same publish claim. The manual route (no autopilot run) runs it before the ledger records the post id. Graph: `POST /{ig_user_id}/media` with `media_type=STORIES` + `image_url`, then `GET /{container}?fields=status_code` until `FINISHED`, then `POST /{ig_user_id}/media_publish`.

- Idempotent: one `instagram_stories` row per carousel. A `published` row short-circuits with no Graph call. The container id is committed before `media_publish`; a crash resumes it (or, past 24 h, reads its status and never posts a second Story when it reports `PUBLISHED`).
- Transient Graph errors are retried, three attempts in total. A permanent error, a missing slide 1, or any unexpected error is stored on the row and returned. The step never raises, so the post's published state never depends on the Story.
- Only the real Graph publisher gets a Story step. Any other publisher has no Story line.
- The publish claim's stale window now covers the Story's worst case too (`CLAIM_HELD_WORST_CASE_SECONDS`).

**Telegram notice.** The published notice reads:

```
✅ Publicado: <permalink>
📲 Story: publicado            (or: 📲 Story falhou: <reason>)
🎵 Adicione uma música pelo app (20s): sugestão: <style>
```

The style comes from `music_style_for(niche, image_style)` (`story_constants.MUSIC_*`): niche words first (accents stripped: AI/IA/tech → `lo-fi eletrônico / synthwave`, cybersecurity → `dark synth`, robotics → `cinematic electronic`), then the image style (`comic_neon` → synthwave, `cinematic` → cinematic electronic), else `lo-fi beats`.

**Migration.** Revision `f8a9b0c1d2e3` adds the `instagram_stories` table (additive). Prod deploys do not run Alembic, so it is applied by hand before the deploy.

### 5.5 Scheduled publishing from Telegram (AE-0370)

Instagram's Graph API has no native scheduling (`media_publish` posts at once) and containers expire 24 h after creation. So the schedule is our own queue: the time is stored on the run, and the containers are created only when the run is due.

**Approve.** The review keyboard's Approve now answers with `🚀 Publicar agora` (`ap:pubnow:<run>`) and `🗓 Agendar` (`ap:sched:<run>`). Publicar agora keeps the AE-0356 path. With `AUTOPILOT_DEFAULT_PUBLISH=next_slot` (default `now`), Approve schedules the next slot directly and says so.

**Agendar.** The next three of the slots `12:00`, `18:00`, `21:00` (America/Sao_Paulo, `schedule_constants.SCHEDULE_SLOTS`), each at least 15 min ahead, rolling over to the next day (`ap:at:<unix seconds>:<run>`, 53 bytes), plus `✏️ Outro horário`. That one sends a ForceReply asking for `HH:MM` (today, else tomorrow) or `DD/MM HH:MM`. Past times and anything more than 30 days ahead are refused with a reply, and the prompt is asked again.

**On a chosen time.** The run moves `awaiting_owner → scheduled` with `scheduled_at` (the compare-and-set makes a double tap act once), then final review is approved (`approved_for_publish`) but the carousel is not released. A refused approve returns the run to `awaiting_owner` with the review keyboard. The owner sees `🗓 Agendado para Ter 20/10 12:00 (reason)` with `🚀 Publicar agora`, `🗓 Mudar dia/horário` (AE-0404) and `❌ Cancelar agendamento`.

**Due tick.** Before the publish job, the worker's Instagram step runs `ScheduledPublishSweep`. Each run with `scheduled_at <= now` moves `scheduled → publishing` (reason `schedule_due`) and is released public. The publish job then posts it on the same tick (quota, containers, Story, notice). A run more than 10 min late (downtime, deploy) still publishes, and the notice line reads `✅ Publicado: <link> (publicado com atraso de N min)`. If the carousel is no longer `approved_for_publish` at its time (sent back or rejected), the run becomes `expired` (reason `schedule_withdrawn`) and nothing is published.

**Cancel and publish now.** `❌ Cancelar agendamento` moves `scheduled → awaiting_owner`, clears `scheduled_at`, and shows the review keyboard again. `🚀 Publicar agora` on a scheduled run moves it to `publishing` and releases it at once. Final review is already approved, so it is not approved again (also after a cancel).

**Day/time picker (AE-0404).** `🗓 Agendar` (on the review keyboard and the publish choice) and `🗓 Mudar dia/horário` (on every scheduled message) open a two-step picker. Step 1 (`ap:d:<yyyymmdd>:<run>`, 50 bytes) lists seven São Paulo days, from today when a recommended slot is still 15 min ahead, else tomorrow, and stars the best days. Step 2 lists the day's four best whole-hour times (`ap:at:<epoch>:<run>`) with each reason in the message text, plus `✏️ Outro horário` and `← Dias` (`ap:days:<run>`). A slot on an `awaiting_owner` run schedules it as above; on a `scheduled` run it moves `scheduled → scheduled` with the new `scheduled_at` (reason `owner_rescheduled`, a compare-and-set, so a due tick that won first makes the tap answer "already"). Recommendations (`domain/recommend.py`) blend per (weekday, hour): the audience (Graph `online_followers`, cached in `instagram_audience_hours` and read at most once a day; a failure is logged and the cache or nothing is used), the engagement `(saved + shares + total_interactions) / reach` of our published posts in that bucket shrunk by `n / (n + 5)`, and the plan prior (POV Tue/Thu 12:00, else 12:00/18:00/21:00). With `AUTOPILOT_DEFAULT_PUBLISH=next_slot` (and always for POV) Approve schedules the best slot of the next seven days.

**Safety.** Only the owner allowlist can tap. The 72 h review expiry scans `awaiting_owner` only, so a `scheduled` run is never expired before its time. Webhook replies are still sent only after the commit.

**Migration.** Revision `a9b0c1d2e3f4` adds the nullable `autopilot_runs.scheduled_at` TIMESTAMPTZ and the index `idx_autopilot_runs_state_scheduled_at (state, scheduled_at)` (additive). Prod deploys do not run Alembic, so it is applied by hand before the deploy.

### 5.6 Ponto de Vista topics and the thesis gate (AE-0377, ADR-0021)

The routine pack is `ops/grokbot/grok-bot/v3/`. A v3 topic carries `mode`
(`news_analysis` = Radar IA, the default when absent, so v2 stays valid, or `pov`) and, for
`pov`, a `thesis_draft` of at most 280 characters.

**Intake.** A `pov` topic without a draft is rejected with `thesis_missing`; a draft with a URL
is rejected with `url_in_text`. Radar IA is capped at one run per São Paulo week (Monday 00:00
to Monday 00:00): a second one is rejected with `weekly_news_cap_reached`, and within one batch
only the best-scored Radar IA topic is queued. POV topics only count against the daily cap.

**Thesis gate.** The scout's thesis is a draft, never the owner's opinion. On its tick the runner
moves a POV run without a confirmed thesis from `queued` to `awaiting_thesis` instead of starting
generation. The worker's Telegram tick sends one prompt per run (recorded in the run's notice
ledger, so a replayed tick never asks twice) with **✅ Confirmar / ✏️ Editar / ❌ Descartar**:

- Confirmar stores the draft as `autopilot_runs.pov_thesis` and moves the run back to `queued`
  in one compare-and-set (`confirm_thesis`), so a double tap starts generation once.
- Editar opens a ForceReply. The owner's reply (trimmed, at most 280 characters, else asked
  again) is stored the same way.
- Descartar moves the run to `rejected`. After 72 h the run expires (`thesis_expired`).

The run then starts a POV carousel: `content_mode=pov`, the confirmed thesis, the
`pov_editorial` image preset and the POV defaults. No photo is picked automatically (follow-up).

**Publish slots.** `domain/pov_schedule.py` defines the POV slots (Tuesday and Thursday 12:00
São Paulo), the POV prior of the AE-0404 slot recommender (section 5.5). A run with a confirmed
`pov_thesis` is a POV run: Approve auto-schedules it (also in `now` mode) for the best
recommended slot of the next seven days, which without insights is the next Tuesday or Thursday
12:00 (at least 15 min ahead); the day/time picker stars those days. Radar IA runs use AE-0370's
12:00/18:00/21:00 as their prior.

**Migration.** Revision `b1c2d3e4f5a6` (after `b0c1d2e3f4a5`, which follows AE-0370's `a9b0c1d2e3f4`) adds the nullable
`topic_candidates.content_mode`, `topic_candidates.thesis_draft` and `autopilot_runs.pov_thesis`
(additive).
## 6. Backend changes (gap → fix)

| Gap found in the codebase | Fix |
|---|---|
| No machine auth (JWT only, 60 min, no refresh: `infrastructure/auth.py`) | Scoped service API key: `X-Api-Key`, stored as an argon2/sha256 hash, scope `autopilot`. It is valid **only** on `/api/autopilot/*`. |
| No auto mode: six gates need a human (`agents/carousel_workflow_nodes.py:192-427`) | `AutopilotRunner` approves gates in-process with the gate's quality checks, and **always stops at `final_review`**. The persona ≥ 70 gate stays enforced. |
| `workflow/start` is synchronous, ~68 s, against the ~100 s Cloudflare cap | The runner calls the service directly from the worker loop, so no HTTP is involved. |
| No outbound notifications (`notification_service.py:275` only logs) | A `TelegramNotifier` adapter behind a `Notifier` protocol, called from the outbox consumer for `content.autopilot.*`. |
| No "carousel finished" event | The runner detects `final_review/awaiting_human` and emits `content.autopilot.ready_for_owner`. |
| IG publish is not idempotent, the post id is not saved, there is no status route (`publishing.py:104-166`, `modules/publishing/application/service.py:149`) | `InstagramPublishJob` persists the container id and post id, and `GET …/publish/instagram/status` is added (the frontend already expects it, `frontend/src/constants/api.ts:49`). |
| The IG token is a static env var with no refresh | Move it to `integration_credentials` and add a worker refresh at 50 days. A Telegram alert fires if the refresh fails or expiry is < 7 days away. |
| `META_IG_ACCESS_TOKEN`, `META_IG_USER_ID`, `CAROUSEL_PUBLIC_BASE_URL` are missing in prod (`docker-compose.prod.yml:60-82`, `deploy.yml:126-148`) | Add them, plus `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `TELEGRAM_OWNER_CHAT_ID`, `GROKBOT_API_KEY_HASH`, to GitHub Secrets → `deploy.yml` → compose. |
| Slide JPEGs go through Cloudflare | Add a Cloudflare WAF skip rule for `/api/carousels/*/slide-images/*`, so Meta's fetcher is not challenged. Verify with `curl -A facebookexternalhit/1.1`. |

**Auto-approve checks per gate.** These are deterministic and live in `modules/autopilot/domain/policy.py`:

- **research:** ≥ 3 sources with content.
- **outline:** the outline length equals the slides the pipeline builds: the presentation
  contract's `slide_count` (7), falling back to `slides_config` only if the contract is
  unreadable (AE-0362). Projects are created with `CAROUSEL_DEFAULT_SLIDES_CONFIG` (7).
- **content:** when persona scores exist, the lowest must be ≥ 70 (a missing `overall` or an
  unreadable entry counts as 0). A run with no persona has no scores; like the engine, the
  voice check is then skipped and the owner's review reads `Persona: not scored` (AE-0364).
  Forbidden phrases (reason `forbidden_phrase`, Measured lists the phrases), blocking
  presentation rules of `content_gate_validation` (reason `content_quality`, AE-0392) and the
  engine's own content-approve refusal still block.
- **design:** `presentation_validation` has no blockers. Blocking rules there are also
  `content_quality`; a missing or rule-less blocking report stays `presentation_validation_blocked`.
- **images:** one `image_assets` hero image per slide the image phase illustrates, counted by
  the pipeline's own filter on the persisted slides (AE-0365): the CTA slide uses the owner
  avatar, so a 7-slide carousel has 6. Every file is a present JPEG with a decodable size (raw
  hero images, not the 1080×1350 slides composed at finalize; AE-0362).

A failed check means `revise` with templated feedback, at most 2×, then **escalate**.
Escalation never approves anything blindly.

**Repair before revise (AE-0392).** When the content or design gate fails on
`content_quality` (or `presentation_validation_blocked`), the runner first runs the owner
"Fix issues" plan (AE-0367) on the checkpoint's `localized_slides`, through the editorial
facade `run_gate_repair`: sentence case, proper nouns, features/summary points from the
outline, `<strong>` balancing, a bounded EN re-translate. The repaired slides go through the
reviewer-edit path (re-validate, sync `slide_drafts`, `translations_en` and the content-gate
report) under the project lock and a lock-version CAS; no re-render. The gate is then read
again: a clean gate is approved without spending a revision (`autopilot_content_autorepaired`
logs the fixed rules). This also runs before an escalation at the revision cap. What is left
is revised with the v2 feedback prompt: `Measured` lists `rule@slide` pairs (at most 10) and
one line per failing slide gives the rule and its current text, asking the model to change
only those slides. A revise still regenerates the whole content phase (the engine has no
per-slide regenerate behind a review decision); the content phase re-drafts each blocking
slide once on its own (AE-0309). A lost CAS waits for the next tick.

**Model fix, then escalate (AE-0401).** With the slide fixer wired (the worker always wires
it), a gate still failing on `content_quality` or `persona_score_below_threshold` after the
repair (a repair no-op included) is **not revised**. Each failing slide (a blocking rule, or
at the content gate a `persona_scores["slide_N"].overall` under 70) is rewritten by the
fast-role model through the editorial facade `run_slide_fix`, in parallel
(`CONTENT_DRAFT_CONCURRENCY`), at most `AUTOPILOT_AUTOFIX_ATTEMPTS` (default 3) times. Each
attempt sends the slide's PT/EN copy, every check it still fails, the persona style guide and
the copy rules (prompt `carousel/v1/slide_fix.yaml`); the strict JSON answer is read
fence-aware, deterministically repaired, re-validated against the deck and re-scored only when
its text changed. A model error or an unparseable answer counts as an attempt. Fixed slides are
written once, through the reviewer-edit path plus their new voice score, under the project lock
and the lock-version CAS (a lost CAS writes nothing: next tick). The gate is read again: clean
is approved; anything left escalates at once with the Telegram detail "slide N: rules. Current
text: "..." (3 fix attempts)". Every attempt logs `autopilot_slide_autofix` (run, project,
slide, attempt, rules before/after, outcome); Langfuse metadata `phase=autofix`,
`agent_name=slide_fixer`. The revise budget is never spent on these reasons; research,
outline, images and forbidden phrases keep revise/escalate. An escalated run is no longer
active, so a gate cannot loop on a repair no-op (prod 2026-10-16 logged one every minute for
50 minutes). Rules: [`docs/backend/slide-copy-validators.md`](../backend/slide-copy-validators.md).

**Telegram webhook security** (`POST /api/telegram/webhook`):

- Require the `X-Telegram-Bot-Api-Secret-Token` header, compared in constant time.
- Accept `callback_query.from.id == TELEGRAM_OWNER_CHAT_ID` only. Ignore everything else silently.
- De-duplicate `update_id`.
- `callback_data` is `ap:<action>:<run_id>`, which fits the 64-byte limit.
- Always `answerCallbackQuery`, so the button spinner stops.
- Edit the keyboard message to show the result, so stale buttons can't be re-used.

---

## 7. Zero-cost bill of materials

| Need | Choice | Cost |
|---|---|---|
| Scout LLM | Cursor CLI `agent`, `grok-4.7-high`, existing plan | $0 new (counts against the plan's usage) |
| Scheduler | systemd timer on the existing droplet | $0 |
| Trends | HN Algolia, HF, RSS, Bluesky, GitHub | $0 |
| Notify + approve | Telegram Bot API (BotFather) | $0 |
| Publish | Instagram API with Instagram Login (own account, Standard Access, no App Review) | $0 |
| Carousel generation | existing providers | existing per-call spend, bounded by `AUTOPILOT_DAILY_CAP=1` |

---

## 8. Risks and pre-flight checks

1. **Cursor plan coverage.** Cursor/X moved to "The X Subscription" on 2026-10-12. Before building anything, confirm on the droplet:
   - `agent status`,
   - `agent --list-models | grep grok-4.7`,
   - one `agent -p` run.

   Set an on-demand spend cap of $0.
2. **Cursor AUP on "bots or scripts".** The wording is ambiguous, but headless mode is documented for automation. Volume is one call per day, so risk is low.
3. **Instagram account type.** It must be **Business or Creator**. If it is linked to a Facebook Page, check Page Publishing Authorization.
   - Only 4:5 renders are accepted; 3:4 fails with error 36003. Current renders are 1080×1350, which is fine.
   - The API allows 2–10 items, and the workflow must cap slides at 10.
4. **Token expiry.** If the IG token fully expires (60 days without a refresh), it can't be recovered. A new one has to be generated by hand, so the refresher and its alert are mandatory.
5. **Deploys.** Pushing to `main` deploys prod. The new Alembic migration must be the single head.
6. **Prompt injection via signals.** Mitigated by four controls:
   - the read-only sandbox,
   - `env -i`,
   - schema validation plus the source allowlist,
   - the human approval gate before publishing.

---

## 9. Delivery plan (tickets for Cursor/Grok implementation, in order)

| # | Ticket | Depends | Feature file? |
|---|---|---|---|
| 0 | Pre-flight spike: Cursor CLI on the droplet with grok-4.7-high; Telegram bot via BotFather; IG Business token. Manual only. | — | no (spike) |
| 1 | `modules/autopilot` skeleton + Alembic migration (4 tables) + constants | — | yes |
| 2 | Service API-key auth, scoped to `/api/autopilot/*` | 1 | yes |
| 3 | Signal collectors (X via `ddgs` web search, HN, HF, RSS, Bluesky, GitHub) + `GET /autopilot/signals`; `XPostResolver` port with `none` default | 2 | yes |
| 4 | Topic intake `POST /autopilot/topics`: schema, source allowlist, dedupe, daily cap | 2,3 | yes |
| 5 | `AutopilotRunner` + gate policy (auto-approve to final_review, revise/escalate) | 1 | yes |
| 6 | `Notifier` protocol + `TelegramNotifier` (album + keyboard, reminders) | 1 | yes |
| 7 | Telegram webhook: secret header, owner allowlist, dedupe, Approve/Rework/Reject | 5,6 | yes |
| 8 | Idempotent `InstagramPublishJob` + status route + persist `ig_post_id` | 1 | yes |
| 9 | IG token store + refresher + expiry alert | 8 | yes |
| 10 | Prod wiring: secrets in `deploy.yml` + compose, Cloudflare skip rule, setWebhook | 7,8,9 | no (config, plus a seeded check) |
| 11 | Grok Bot routine pack + `POST /autopilot/x-signals` + `POST /autopilot/scout-failed` (§5.2) | 2,3,4,6 | yes |

**MVP cut.** Tickets 0, 1, 2, 4, 5, 6, 7, 8, 10, 11 make the loop work end to end.
Tickets 3 and 9 can start minimal: X web search + HN + HF, and a manual token refresh with an alert.
