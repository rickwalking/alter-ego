# AE-0635 — Repost quality: show the source size in the prompt, warn below 720p, encode higher

Status: In Development
Tier: T1
Priority: High
Type: Bug
Area: Backend
Owner: Pedro
Agent Lane: developer → qa → release
Branch: fix/ae-0633-deploy-script-length
Kanban Card: TBD
Created: 2026-11-20
Updated: 2026-11-20

## Goal

The owner sees how good the source video is before approving a repost, and a good source keeps more of its quality.

## Problem

The first published repost (Df-vVpZAOv_, from media 17979453281811963) looked much worse than the original. Graph's
`media_url` for that 272-day-old Reel is a 360x640, 134 kbps copy (CDN tag `…CLIPS.C3.360…`). The Instagram app
plays a better DASH stream that the API does not expose. A 194-day-old Reel (DYJJjNlo0-x) comes as 720x1280 at
1.3 Mbps. Upscaling to 1080x1920 cannot restore the detail. The render used CRF 23 and the `veryfast` preset.

## Scope

- After the download, ffprobe the source size (`ffprobe_size_args`, `parse_size`, `FfmpegRenderer.size`) and carry
  it in `RenderedFiles.source_size` and `ApprovalNotice.source_size`.
- The Telegram prompt shows "Fonte do vídeo: WxH"; below 720 on the short side it warns that the repost will look
  blurry. Owner decision: warn, do not refuse.
- Encode: CRF 20, `medium` preset, Lanczos scaling. Measured on prod (2 vCPU) for 90 s of a 720p source: 217 s
  (limit 600 s), 4.3 Mbps, 48 MB. Before: 84 s, 2.5 Mbps.

## Non-Goals

- No refusal of low-quality sources (owner chose a warning instead).
- No storing the size: a caption-edit refresh of the prompt does not repeat the line. That would need a column.
- No upload of an original file (follow-up if wanted).

## Acceptance Criteria

- [x] AC1 The prompt names the source size; below 720p it carries the low-quality warning; unknown size adds no line.
- [x] AC2 The render uses CRF 20, the medium preset and Lanczos scaling.
- [x] AC3 A missing or unreadable source size reads as unknown and never fails the render.
- [ ] AC4 Deployed; the next repost prompt shows the source size.

## Gherkin

`backend/tests/features/autopilot_repost_publish_ae0629.feature`: "The prompt shows the source video's size and
warns when it is low", "The render command".

## Files Touched

- `backend/src/rag_backend/modules/autopilot/{repost_constants.py, domain/repost_render.py, domain/repost_copy.py,
  application/repost_tick.py, application/repost_tick_ports.py, infrastructure/repost_video.py,
  infrastructure/repost_studio.py}`
- `backend/tests/unit/modules/autopilot/test_repost_quality_ae0635.py`, `test_repost_render_ae0629.py`,
  `test_repost_tick_ae0629.py`, the AE-0629 feature

## Test Evidence

- `uv run pytest tests/unit/modules/autopilot tests/integration/test_autopilot_repost_api_ae0628.py` → all passed,
  including a real ffmpeg size read.
- Single gates format, lint, lint-diff, strict-diff, type, imports, arch-ratchet, docstrings, dead-code,
  gherkin-refs, comments, openapi-fresh, duplication → PASS.
