# AE-0341 — fix the frontend container healthcheck (bind HOSTNAME, or probe the real one)

Status: Ready
Tier: T1
Priority: Medium
Type: Bug
Area: Frontend
Owner: Unassigned
Agent Lane: developer → qa → release
Branch: TBD
Kanban Card: TBD
Created: 2026-09-15
Updated: 2026-09-15

## Goal

`alter-ego-frontend-1` must report **healthy** when it is serving. A permanently
red healthcheck is a broken instrument — it trains everyone to ignore the one
signal that should mean something.

## Problem

`docker compose ps` has shown `alter-ego-frontend-1 … (unhealthy)` continuously
for roughly eight weeks, while the site is fine: nginx's `frontend:3000` upstream
works and `/` returns 200, `/login` 200, `/dashboard` 307→login.

Cause: Next.js standalone binds to the `HOSTNAME` env var. In the container that
resolves to the **container id**, so `server.js` listens on the eth0 address only
(`172.18.0.x:3000`). The healthcheck in `frontend/Dockerfile:45-46` probes
loopback:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1
```

Nothing is listening on `127.0.0.1:3000`, so the probe is refused and the
container is marked unhealthy forever — even though it serves every real request
through the docker network address.

Two consequences beyond the noise: `depends_on: service_healthy` can never be
used for the frontend, and a genuine frontend outage would look identical to
today's steady state.

## Scope

- Set `HOSTNAME=0.0.0.0` for the frontend service (compose `environment:` and/or
  the Dockerfile `ENV`) so the standalone server listens on all interfaces —
  **or** change the probe to target `$HOSTNAME` instead of `localhost`. Prefer
  binding `0.0.0.0`: it also makes the container behave predictably behind any
  network setup.
- Verify `/api/health` is actually the right probe target and returns 200 without
  authentication.
- Confirm the change in prod: container reports `healthy`.

## Non-Goals

- Adding `depends_on: service_healthy` wiring for the frontend (possible follow-up
  once the probe is trustworthy).
- Changing the nginx upstream (it already works).
- Touching the backend or Postgres healthchecks.

## Acceptance Criteria

- [ ] `docker compose -f docker-compose.prod.yml ps` reports the frontend as
      `healthy` after a deploy.
- [ ] `docker exec alter-ego-frontend-1 wget -qO- http://localhost:3000/api/health`
      succeeds inside the container.
- [ ] The site still serves through nginx (`/` 200, `/login` 200,
      `/dashboard` 307) after the change.
- [ ] The healthcheck fails when the app is genuinely down — proven by stopping
      the node process (or pointing the probe at a dead path) and observing the
      container flip to unhealthy.

## Gherkin Scenarios

```gherkin
Feature: The frontend healthcheck tells the truth

  Scenario: A serving frontend is healthy
    Given the frontend container is serving requests through nginx
    When Docker runs the healthcheck
    Then the container is reported healthy

  Scenario: A broken frontend is unhealthy
    Given the frontend process is not serving
    When Docker runs the healthcheck
    Then the container is reported unhealthy
```

## Affected Areas

- Backend: no
- Frontend: `frontend/Dockerfile` and/or `docker-compose.prod.yml` frontend service
- Database: no
- API: no
- Tests: manual/deploy verification plus the deliberate-failure check
- Docs: deployment notes
- Prompts/LLM: no
- Observability: this IS the observability fix
- Deployment: yes

## Dependencies

- Blocks: any future use of frontend health as a gate
- Blocked by: none
- Related: AE-0333 (deploy health assertion)

## Implementation Plan

1. Set `HOSTNAME=0.0.0.0` on the frontend service.
2. Confirm the in-container loopback probe succeeds.
3. Deploy; confirm `healthy` in `docker compose ps`.
4. Prove the negative: make the app unreachable and observe `unhealthy`.

## QA Checklist

- [ ] Security reviewed (binding 0.0.0.0 inside the container is not published to the host)
- [ ] Code quality reviewed
- [ ] Acceptance criteria validated
- [ ] Edge cases tested (probe during startup grace period)
- [ ] Orphan/unfinished code checked

## Progress Log

### 2026-09-15

Ticket created from the AE-0330 session handoff. Confirmed at
`frontend/Dockerfile:45-46`; the prod container has been unhealthy for ~8 weeks
while serving normally.

## Files Touched

Pending.

## Test Evidence

Pending. Deployment/config ticket (AE-0153 no-`.feature` path available): no
user-visible behaviour change — the app already serves. Verification is the
container health state plus the deliberate-failure check.

## QA Report

Pending.

## Decision Log

Pending.

## Blockers

None.

## Final Summary

Pending.
