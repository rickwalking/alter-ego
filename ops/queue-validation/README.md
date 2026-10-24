# Generation queue: disposable-droplet validation

The generation worker goes live when its PR merges (Pedro, 2026-10-23: no feature flag), so the
load and chaos checks of the generation queue run **before the merge**, on a throwaway DigitalOcean droplet the
size of prod, against the PR branch. `validate.sh` does all of it and destroys the droplet on exit,
even when a step fails (`trap teardown EXIT INT TERM`).

## What it proves

| Check | Pass condition |
|---|---|
| Web latency while carousels generate | p95 of the four public routes during generation ≤ 1.2 × the idle p95 on the same droplet (`p95-verdict.json`) |
| Memory | no container `OOMKilled`, no kernel "out of memory" line (`report.tsv`), peaks in `memory-samples.tsv` |
| Worker killed mid-phase | the job is picked again and the run completes; `generation_runs.attempts` shows the interrupted start |
| Full deploy mid-run | same deploy sequence as `deploy.yml` (build, drain the worker, `down`, one-shot, `up`); the run resumes and completes |
| Revert strands nothing | after a drain and `generation_queue_rollback --apply`, the merge base is deployed (no worker); the in-process runner of the reverted code finishes every queued and in-flight autopilot run (`revert-verdict.txt`) |
| No duplicates | `duplicate_ready_notices` = 0 (one owner notice, so one Telegram message, per run) and `duplicate_builds_of_one_version` = 0 |
| No production credential | `credential-check.txt`: every value of the droplet `.env` hashed against the production hashes; any match aborts before the stack starts |
| No production egress | the cloud firewall closes all outbound traffic after the image build; the script fails if the droplet can still reach `api.telegram.org` |

Every outbound service is replaced by `mock_upstream.py` on the compose network: an OpenAI-compatible
chat endpoint (the GLM base URL), the Grok Bot image webhook (answers with a generated PNG through the
real callback route) and the topic source pages. The droplet runs the production compose file as it is
on the branch (Langfuse moves to Langfuse Cloud, so the run measures the box without it) plus
`compose.validation.yml` (plain-HTTP nginx, no certbot, no OpenCode sidecar, the mock). The data is
synthetic: `seed.py` creates an owner, the "Pedro" persona and N queued themes directly in the database.
No production data leaves prod.

## Inputs (all outside the repo, never committed or logged)

- `DO_TOKEN_FILE`: a file holding a DigitalOcean API token (scoped, short-lived). Read into a 0600
  header file in a temp dir that the teardown removes.
- `PROD_HASHES_FILE`: SHA-256 digests of the production `.env` values, one per line. Produce it
  read-only, without the values ever leaving the box:
  `ssh root@<prod> "cut -d= -f2- /opt/alter-ego/.env | sed -e \"s/^['\\\"]//\" -e \"s/['\\\"]\$//\" | grep -v '^$' | while IFS= read -r v; do printf %s \"\$v\" | sha256sum | cut -d' ' -f1; done" > ~/prod-hashes.txt`

## Run

```bash
DO_TOKEN_FILE=~/.config/do-validation-token PROD_HASHES_FILE=~/prod-hashes.txt \
  DO_REGION=nyc1 bash ops/queue-validation/validate.sh
```

Optional: `DO_SIZE` (default `s-2vcpu-4gb`, the prod size), `VALIDATION_THEMES` (3),
`VALIDATION_LOAD_SECONDS` (240), `VALIDATION_RUN_TIMEOUT_SECONDS` (3600), `MOCK_LATENCY_SECONDS`
(20 per LLM call, set on the droplet's compose). Results land in `~/queue-validation-results/<name>/`
and are attached to the PR.

Cost: `s-2vcpu-4gb` is billed hourly at about US$0.036/h; a run takes 1.5-2 h (image build ≈ 25 min,
baseline 4 min, three generations with the two chaos steps, report), so well under US$0.10.

## Production mode (`--target prod`)

Pedro merged the worker without the disposable-droplet run (rollback = revert) and asked for a gentle validation on
the live droplet instead, **run only when he says go**, after the merge is deployed:

```bash
bash ops/queue-validation/validate.sh --target prod
```

`prod_validate.py` (laptop) and `prod_qa_run.py` (inside the prod backend container, sent over ssh stdin) do this:

1. **Refuses** between 11:05 and 13:30 UTC, while a deploy workflow is queued or running, when `/api/health` is not
   200, when any other generation run is active, or when a QA project already exists.
2. **Idle baseline:** 180 s of the four public pages (`/`, `/api/health`, `/blog`, `/carousels`) at 2 req/s from the
   laptop; the same load keeps running for the whole run (`load_p95.py`). Nothing heavier.
3. **One QA carousel**, `[QA <date>] queue validation: …`, created as the owner through the dashboard API
   (`POST /api/carousels`, `POST …/workflow/start`) with a token minted in memory in the container from the app
   settings (never printed). Not autopilot: no Telegram review, no Instagram publish. Each gate is approved
   (`…/workflow/resume`, so every later phase runs in the worker) up to the final review, which is never approved.
4. **Chaos**, each once, only while a worker job of the QA run is running and no other generation run is active:
   `docker kill` of `generation-worker` during the first worker job (then `up -d` if the restart policy has not
   brought it back), and `docker compose restart generation-worker` during a later job (no site downtime).
5. **Every 15 s:** `docker stats`, each container's `OOMKilled` and restart count, host `free -m`, and the health
   route (`memory-samples.tsv`, `steps.jsonl`).
6. **Aborts** on two non-200 health checks in a row, a rolling p95 (last 120 requests) over 3x the idle baseline, any
   `OOMKilled`, or less than 300 MiB available.
7. **Always, also on abort or Ctrl-C:** `verify` (duplicate images per slide and prompt, duplicate artifact builds,
   the run's `generation_runs` attempts and phase attempts, nothing active or `in_progress`), then `cleanup` (cancel
   its queued runs and their PgQueuer jobs, wait up to 20 min for a running phase, `DELETE /api/carousels/<id>`,
   then remove its `generation_runs`, image, build and checkpoint rows). `report.json` holds the outcome, the p95
   verdict, the verify and the leftovers before and after the purge.

Results land in `~/queue-validation-results/prod-<UTC stamp>/`. `PROD_HOST`, `PROD_BASE_URL` and
`VALIDATION_RESULTS` override the defaults. The disposable-droplet mode (`validate.sh` without `--target`) stays
for later.
