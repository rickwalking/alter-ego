#!/usr/bin/env node
/**
 * Enforce frontend feature/module boundaries (AE-0083, AE-0136) — the
 * cross-context import ratchet that mirrors the backend ratchet (AE-0082).
 *
 * Run as part of:
 *   npm run lint            # eslint + this check (+ url:check + lint:circular)
 *   npm run lint:boundaries # this check only
 *
 * Rules (during the Phase 7 feature -> module migration window):
 *   - features layer: a file in `features/A/**` MUST NOT import `@/features/B/...`
 *     internals (B != A).
 *   - modules public contract: ANY consumer (a feature, `app/`, or another
 *     module) MUST import a module via its barrel (`@/modules/<m>` or
 *     `@/modules/<m>/index`), never a deep internal `@/modules/<m>/<internal>`.
 *   - Shared layers (components/, lib/, constants/, i18n/, schemas/) and a
 *     context's own files are always allowed (never inspected).
 *   - Existing violations listed in the committed baseline are grandfathered.
 *   - Any NEW cross-context import errors and fails the build.
 *   - If the total violation count rises above the baseline `count`, fail.
 *
 * Regenerate the baseline (only ever to ratchet DOWN) with:
 *   npm run boundaries:baseline
 */

import { existsSync, readFileSync } from "node:fs";

import { BASELINE_PATH } from "./feature-boundary.config.mjs";
import {
  scanCrossFeatureImports,
  violationKey,
} from "./feature-boundary-scan.mjs";

const REGEN_HINT = "Run `npm run boundaries:baseline` to (re)generate it.";

/**
 * @returns {{ count: number, allowlist: string[] }}
 */
function loadBaseline() {
  if (!existsSync(BASELINE_PATH)) {
    process.stderr.write(
      `Feature/module-boundary baseline missing at ${BASELINE_PATH}. ${REGEN_HINT}\n`,
    );
    process.exit(1);
  }
  const parsed = JSON.parse(readFileSync(BASELINE_PATH, "utf8"));
  return { count: parsed.count ?? 0, allowlist: parsed.allowlist ?? [] };
}

function main() {
  const { count: baselineCount, allowlist } = loadBaseline();
  const allowed = new Set(allowlist);
  const violations = scanCrossFeatureImports();

  const newViolations = violations.filter(
    (violation) => !allowed.has(violationKey(violation)),
  );

  // Ratchet on DISTINCT file -> foreign-context relationships (the allowlist
  // unit), so two imports of the same foreign context from one file count once.
  const distinctCount = new Set(violations.map(violationKey)).size;

  const errors = [];

  for (const violation of newViolations) {
    errors.push(
      `NEW cross-context import: ${violation.file} imports "${violation.specifier}" ` +
        `(context "${violation.from}" must not import internals of context "${violation.to}"). ` +
        `Import the module's public contract (its barrel) or use a shared layer ` +
        `(components/, lib/, constants/, i18n/, schemas/) instead.`,
    );
  }

  if (distinctCount > baselineCount) {
    errors.push(
      `Cross-context import count rose to ${distinctCount} (baseline ceiling ${baselineCount}). ` +
        `New cross-context imports are not allowed.`,
    );
  }

  if (errors.length > 0) {
    process.stderr.write("\nFeature/module boundary check FAILED:\n");
    for (const error of errors) {
      process.stderr.write(`  - ${error}\n`);
    }
    process.stderr.write(
      `\nNew cross-context imports must be removed (do NOT add to the baseline). ${REGEN_HINT}\n`,
    );
    process.exit(1);
  }

  process.stdout.write(
    `Feature/module boundary check OK: ${distinctCount} grandfathered cross-context relationship(s), ` +
      `baseline ceiling ${baselineCount}, 0 new.\n`,
  );
}

main();
