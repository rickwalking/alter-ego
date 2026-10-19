# carousel_gate_repair prompts

## v1 — `field_repair.yaml` (AE-0430)

The content-gate targeted repair. When the content gate blocks (after drafting, after
translation, after a "Feedback para revisão" revision), the failing fields and only those
are sent to the fast model, each with its slide/locale/field path, current text, the exact
limit the validator enforces, the problems found, the slide heading and (EN fields) the PT
source. The answers are patched in by path and re-validated, at most 2 rounds; what is
still blocking stays visible in `content_gate_validation`.

Code: `application/services/carousel/content_gate_repair.py` (loop + model call) and
`content_gate_repair_targets.py` (targets, PT->EN structure fill, patching).
