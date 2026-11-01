# AE-0589 — Rate limits see nginx's address: one login bucket for every user

Status: In Progress
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0589-rate-limit-client-ip
Kanban Card: TBD
Created: 2026-11-01
Updated: 2026-11-01

## Goal

The backend rate limits key on the real visitor, so login and change-password (5 per minute) give each visitor its own
bucket, and nobody can choose their key by sending a forged `X-Forwarded-For`.

## Problem

Confirmed read-only on prod (2026-11-01): backend access logs show every `/api/auth/*` call from `172.18.0.9`
(`alter-ego-nginx-1`), other traffic from `172.18.0.8` (the frontend container) and `127.0.0.1` (healthchecks).
`backend/Dockerfile` ran `uvicorn ... --host 0.0.0.0 --port 8000` with `FORWARDED_ALLOW_IPS` unset, so uvicorn trusted
forwarded headers from `127.0.0.1` only and slowapi's `get_remote_address` saw nginx for everyone. A few bad logins
locked every user out. nginx itself sees a Cloudflare edge as the peer (no `real_ip` config), so it could not have
sent the visitor even if the backend had trusted it.

Pedro's decision (2026-11-01): trust forwarded client addresses only from the proxy (nginx), not from any other source.

## Scope

- `docker-compose.prod.yml`: pin the default network (`172.18.0.0/16`, the subnet prod already uses; dynamic
  addresses from `ip_range 172.18.0.0/17` only), give nginx the fixed address `172.18.200.10`, and set the backend's
  `FORWARDED_ALLOW_IPS: "127.0.0.1,172.18.200.10"` (hard-coded, not a secret; no deploy.yml change).
- `backend/Dockerfile`: run uvicorn with an explicit `--proxy-headers` (the env supplies the trusted peers).
- `nginx/nginx.conf.ssl` and `nginx/nginx.conf`: `set_real_ip_from` Cloudflare's published ranges with
  `real_ip_header CF-Connecting-IP`, so `$remote_addr` is the visitor (also fixes nginx's own `limit_req` zones, which
  keyed on Cloudflare edges); `X-Forwarded-For $remote_addr` on every location instead of
  `$proxy_add_x_forwarded_for`.
- Deployment guide section on client addresses and rate limits.

## Non-Goals

- Trusting the frontend container. Its server-side calls (the no-JavaScript `/auth/login` form route) go straight to
  `backend:8000`, do not forward the visitor address, and keep keying on the frontend container. nginx's per-visitor
  `limit_req` on `/auth/login` covers that path. The JS login and change-password go browser → nginx → backend.
- Changing limits, keys or slowapi code.

## Acceptance Criteria

- [x] AC1 A request from nginx with `X-Forwarded-For: <client>` keys the limiter on `<client>`.
- [x] AC2 A forged `X-Forwarded-For` from any other peer (outside, the frontend container) is ignored; the key is the
  peer's own address.
- [x] AC3 `X-Forwarded-For: <fake>, <client>` from nginx keys on `<client>` (right-most untrusted hop; uvicorn 0.44).
- [x] AC4 Two clients through nginx get separate login buckets: A gets 429 on the 6th try, B still gets 401.
- [x] AC5 The loopback healthcheck (`/health` from 127.0.0.1) still answers 200.
- [x] AC6 A config test asserts the Dockerfile, compose and both nginx configs, and seeded wrong configs (trust `*`, a
  subnet or another container, no proxy headers, unpinned nginx or nginx inside `ip_range`, appended or copied
  `X-Forwarded-For`, missing or trust-all `real_ip`) are reported.

## Gherkin Scenarios

- `backend/tests/features/rate_limit_client_ip_ae0589.feature`

## Repro Steps

1. Run the app behind `ProxyHeadersMiddleware` with uvicorn's default trust (`127.0.0.1`), peer = nginx.
2. POST bad logins with different `X-Forwarded-For` values → the 6th from any client gets 429 (shared bucket).

## Affected Areas

- [x] Backend
- [ ] Frontend
- [x] Tests
- [x] Infra (compose, nginx, Dockerfile)

## Dependencies

None.

## Progress Log

### 2026-11-01

uvicorn 0.44.0 (locked) reads `FORWARDED_ALLOW_IPS`, accepts CIDRs and picks the right-most untrusted
`X-Forwarded-For` hop. Pinned nginx instead of trusting the subnet so the frontend and other containers stay
untrusted; a static address outside `ip_range` checked on local Docker 29.8. Both nginx configs pass `nginx -t` in
`nginx:alpine`. The ASGI tests fail on the old trust (3 of 7: AC1, AC3, AC4) and pass with the new one; the config
rules report all three old files.

## Files Touched

- `docker-compose.prod.yml`
- `backend/Dockerfile`
- `nginx/nginx.conf.ssl`
- `nginx/nginx.conf`
- `backend/src/rag_backend/api/middleware/rate_limiting.py` (docstring only)
- `docs/deployment/DEPLOYMENT_GUIDE.md`
- `backend/tests/features/rate_limit_client_ip_ae0589.feature`
- `backend/tests/integration/test_rate_limit_client_ip_ae0589.py`
- `backend/tests/unit/scripts_ci/proxy_client_ip_rules.py`
- `backend/tests/unit/scripts_ci/test_proxy_client_ip_config_ae0589.py`

## Test Evidence

Pending full gate run.

## QA Report

Pending.

## Blockers

None.

## Final Summary

Pending.
