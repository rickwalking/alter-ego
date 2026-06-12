# Modularization Baseline — 2026-06 (AE-0077)

**Method:** `scripts/metrics/baseline_loc.sh` (committed). LOC = physical
lines (`wc -l`). Classification: tests = `*.test.*`, `*.spec.*`,
`__tests__/`, `src/test/`; stories = `*.stories.*`; production = the
rest. Output is sorted and timestamp-free; two consecutive runs were
byte-identical (verified).

## Frontend (`frontend/src`, *.ts/*.tsx)

| Class | Files | Lines |
|---|---:|---:|
| Production | 300 | 25,403 |
| Tests | 74 | 15,867 |
| Stories | 33 | 566 |
| **All** | **407** | **41,836** |

### Per-feature (production only)

| Feature | Files | Lines |
|---|---:|---:|
| blog | 23 | 2,064 |
| create | 14 | 2,093 |
| dashboard | 18 | 938 |
| publish | 12 | 1,077 |
| knowledge | 11 | 934 |
| workflow | 11 | 752 |
| chat | 4 | 426 |
| rubrics | 2 | 146 |
| persona | 2 | 144 |
| carousel | 1 | 133 |
| personas | 1 | 91 |
| analytics | 1 | 50 |

Five plan-named features (create/carousel/publish/blog/workflow):
**6,119 production lines**.

## Backend (`backend/src`, *.py)

| Class | Files | Lines |
|---|---:|---:|
| Production | 368 | 44,756 |
| Tests (backend/tests) | 168 | 30,027 |
| carousel services subtotal | 72 | 12,405 |

## Discrepancy resolution

The research report's frontend figures (406 files / 41,638 lines) match
this baseline's **all-classes** totals (407 / 41,836) within drift — the
original methodology silently included tests and stories. The plan's
correction notes assumed a measurement error; it was a classification
omission. The 15,036-line five-feature figure likewise included test
code; the production figure is 6,119.

## Estimate consequence

Phase 7 (frontend alignment) was sized against the inflated figure, so
the re-measured production surface (~25.4k total, ~6.1k in the five
features) **confirms 1-2 weeks is sufficient** and removes the main
uncertainty behind the ±25% bracket. Revised overall estimate:
**11-21 engineer-weeks, confidence ±15%** (remaining variance is
Phase 2.5 evidence and the AE-0075 checkpoint findings, not frontend
size).
