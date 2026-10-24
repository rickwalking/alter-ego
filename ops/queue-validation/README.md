# Generation queue: disposable-droplet validation

The generation worker goes live when its PR merges (Pedro, 2026-10-23: no feature flag), so the
load and chaos checks of ADR-0026 run **before the merge**, on a throwaway DigitalOcean droplet the
size of prod, against the PR branch. `validate.sh` does all of it and destroys the droplet on exit,
even when a step fails (`trap teardown EXIT INT TERM`).

## What it proves

| Check | Pass condition |
|---|---|
| Web latency while carousels generate | p95 of the four public routes during generation ≤ 1.2 × the idle p95 on the same droplet (`p95-verdict.json`) |
| Memory | no container `OOMKilled`, no kernel "out of memory" line (`report.tsv`), peaks in `memory-samples.tsv` |
| Worker killed mid-phase | the job is picked again and the run completes; `generation_runs.attempts` shows the interrupted start |
| Full deploy mid-run | same deploy sequence as `deploy.yml` (build, drain the worker, `down`, one-shot, `up`); the run resumes and completes |
| No duplicates | `duplicate_ready_notices` = 0 (one owner notice, so one Telegram message, per run) and `duplicate_builds_of_one_version` = 0 |
| No production credential | `credential-check.txt`: every value of the droplet `.env` hashed against the production hashes; any match aborts before the stack starts |
| No production egress | the cloud firewall closes all outbound traffic after the image build; the script fails if the droplet can still reach `api.telegram.org` |

Every outbound service is replaced by `mock_upstream.py` on the compose network: an OpenAI-compatible
chat endpoint (the GLM base URL), the Grok Bot image webhook (answers with a generated PNG through the
real callback route) and the topic source pages. The droplet runs the full production compose file
(Langfuse stack included, for a realistic memory budget) plus `compose.validation.yml` (plain-HTTP
nginx, no certbot, no OpenCode sidecar, the mock). The data is synthetic: `seed.py` creates an owner,
the "Pedro" persona and N themes through the real topic intake API. No production data leaves prod.

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
