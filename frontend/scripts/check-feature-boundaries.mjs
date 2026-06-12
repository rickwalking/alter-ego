#!/usr/bin/env node
/**
 * Enforce frontend feature module boundaries (AE-0083) — the cross-feature
 * import ratchet that mirrors the backend ratchet (AE-0082).
 *
 * Run as part of:
 *   npm run lint            # eslint + this check
 *   npm run lint:boundaries # this check only
 *
 * Rules:
 *   - A file in `features/A/**` MUST NOT import `@/features/B/...` (B != A).
 *   - Shared layers (components/, lib/, constants/, i18n/, schemas/) and a
 *     feature's own files are always allowed (never inspected).
 *   - Existing violations listed in the committed baseline are grandfathered.
 *   - Any NEW cross-feature import errors and fails the build.
 *   - If the total violation count rises above the baseline `count`, fail.
 *
 * Regenerate the baseline with: npm run boundaries:baseline
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
      `Feature-boundary baseline missing at ${BASELINE_PATH}. ${REGEN_HINT}\n`,
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

  // Ratchet on DISTINCT file -> foreign-feature relationships (the allowlist
  // unit), so two imports of the same foreign feature from one file count once.
  const distinctCount = new Set(violations.map(violationKey)).size;

  const errors = [];

  for (const violation of newViolations) {
    errors.push(
      `NEW cross-feature import: ${violation.file} imports "${violation.specifier}" ` +
        `(feature "${violation.from}" must not import internals of feature "${violation.to}"). ` +
        `Use a shared layer (components/, lib/, constants/, i18n/, schemas/) instead.`,
    );
  }

  if (distinctCount > baselineCount) {
    errors.push(
      `Cross-feature import count rose to ${distinctCount} (baseline ceiling ${baselineCount}). ` +
        `New cross-feature imports are not allowed.`,
    );
  }

  if (errors.length > 0) {
    process.stderr.write("\nFeature boundary check FAILED:\n");
    for (const error of errors) {
      process.stderr.write(`  - ${error}\n`);
    }
    process.stderr.write(
      `\nNew cross-feature imports must be removed (do NOT add to the baseline). ${REGEN_HINT}\n`,
    );
    process.exit(1);
  }

  process.stdout.write(
    `Feature boundary check OK: ${distinctCount} grandfathered cross-feature relationship(s), ` +
      `baseline ceiling ${baselineCount}, 0 new.\n`,
  );
}

main();
