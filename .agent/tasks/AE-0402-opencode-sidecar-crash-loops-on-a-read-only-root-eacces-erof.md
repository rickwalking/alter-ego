# AE-0402 — OpenCode sidecar crash-loops on a read-only root (EACCES/EROFS)

Status: In Development
Tier: T1
Priority: P0
Type: Bug
Area: infra
Owner: Claude (hotfix)
Agent Lane: developer → release
Branch: fix/ae-0402-opencode-sidecar-perms
Kanban Card: TBD
Created: 2026-10-16
Updated: 2026-10-16

## Goal

The AE-0399 `opencode` sidecar starts and serves sessions in prod, with its root still read-only.

## Problem

After the AE-0399 deploy (2026-10-16), `alter-ego-opencode-1` crash-looped. There were three causes:
1. The `opencode_data` volume and the compose tmpfs mounts are root-owned, while the agent runs as uid 10001 (`EACCES: mkdir ~/.local/share/opencode/log`, `~/.cache/opencode`, `~/.config/opencode`, `~/.local/state/opencode`).
2. OpenCode writes into its install dir (`~/.opencode/.gitignore`, EROFS), and npm installs a plugin under home. The session API answered `UnknownError`.
3. A volume mounted inside a tmpfs home gets root-owned parent directories.

## Scope

- **Image:** move the binary to `/usr/local/bin`. Data goes to `/data/opencode` (`XDG_DATA_HOME=/data`), created as 10001.
- **Compose:** `/home/opencode` becomes a 10001-owned tmpfs (512 MB), with `uid/gid/mode` on every tmpfs. The volume is mounted at `/data/opencode`.
- **Non-change:** the read-only root, `cap_drop: ALL`, no-new-privileges, no ports and no secrets are all kept.

## Non-Goals

- **No backend change.** This is infra only, with no public or user-visible behaviour change, so a `.feature` is not required (AE-0153). The verification is a local container run with the prod flags.

## Acceptance Criteria

- [x] AC1: With the prod flags (read-only, cap_drop ALL, the tmpfs set, a fresh volume), the container stays up.
- [x] AC2: `POST /session` returns a session id with Basic auth; `DELETE /session/{id}` returns 200; without auth it returns 401.
- [x] AC3: There are no EACCES/EROFS errors in the logs; data lands on the volume.

## Gherkin Scenarios

None (infra-only, no behaviour change; see Non-Goals).

## Delta

### ADDED

- None.

### MODIFIED

- `ops/opencode/Dockerfile`, `docker-compose.prod.yml`

### REMOVED

- None.

## Affected Areas

- Backend: none
- Frontend: none
- Database: none
- API: none
- Tests: local container verification
- Docs: this ticket
- Prompts/LLM: none
- Observability: none
- Deployment: opencode service mounts

## Dependencies

- Blocks: free DeepSeek via the sidecar (AE-0399)
- Blocked by: none
- Related: AE-0399

## Implementation Plan

1. Fix the image layout and the mounts.
2. Verify locally with the prod flags.

## QA Checklist

- [x] Security reviewed (root still read-only; only tmpfs and the data volume are writable)
- [x] Code quality reviewed
- [x] Acceptance criteria validated
- [x] Edge cases tested (fresh volume)
- [x] Orphan/unfinished code checked

## Progress Log

### 2026-10-16

Found right after the AE-0399 deploy. The prod volume was chowned by hand to 10001.

## Files Touched

See Delta.

## Test Evidence

- **Local run with the prod flags:** the container stays up; session create gives `ses_…` and delete gives 200; 0 EACCES/EROFS lines.

## QA Report

Pending (hotfix fast path).

## Decision Log

- 2026-10-16: tmpfs over the whole home, plus data outside home. OpenCode writes to several home paths at runtime, and this keeps the root read-only without listing each path.

## Blockers

None.

## Final Summary

Pending.
