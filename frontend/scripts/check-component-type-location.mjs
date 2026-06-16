#!/usr/bin/env node
/**
 * Enforce the frontend component-type-location convention (AE-0144) — the
 * "13x class" ratchet that mirrors the feature/module-boundary ratchet
 * (`check-feature-boundaries.mjs` + `feature-boundary-baseline.json`).
 *
 * Convention: a component (`*.tsx`) or hook (`use-*.ts`) file under
 * `src/modules/**` MUST NOT declare object-shape types inline — they belong in
 * a colocated `types.ts`. See `component-type-location.config.mjs`.
 *
 * Run as part of:
 *   npm run lint                  # eslint + boundaries + url:check + circular + THIS
 *   npm run lint:component-types  # this check only
 *
 * Rules:
 *   - Existing inline declarations listed in the committed baseline are
 *     grandfathered.
 *   - Any NEW inline declaration (a file/kind/name not in the baseline) fails.
 *   - If the total count rises above the baseline `count`, fail.
 *   - The baseline is DOWN-ONLY: regenerate it (only ever to ratchet DOWN) with
 *     `npm run component-types:baseline`.
 */

import { existsSync, readFileSync } from "node:fs";

import { BASELINE_PATH } from "./component-type-location.config.mjs";
import {
  scanInlineComponentTypes,
  violationKey,
} from "./component-type-location-scan.mjs";

const REGEN_HINT = "Run `npm run component-types:baseline` to (re)generate it.";

/**
 * @returns {{ count: number, allowlist: string[] }}
 */
function loadBaseline() {
  if (!existsSync(BASELINE_PATH)) {
    process.stderr.write(
      `Component-type-location baseline missing at ${BASELINE_PATH}. ${REGEN_HINT}\n`,
    );
    process.exit(1);
  }
  const parsed = JSON.parse(readFileSync(BASELINE_PATH, "utf8"));
  return { count: parsed.count ?? 0, allowlist: parsed.allowlist ?? [] };
}

function main() {
  const { count: baselineCount, allowlist } = loadBaseline();
  const allowed = new Set(allowlist);
  const violations = scanInlineComponentTypes();

  const newViolations = violations.filter(
    (violation) => !allowed.has(violationKey(violation)),
  );

  // Ratchet on DISTINCT file/kind/name declarations (the allowlist unit).
  const distinctCount = new Set(violations.map(violationKey)).size;

  const errors = [];

  for (const violation of newViolations) {
    errors.push(
      `NEW inline ${violation.kind} "${violation.name}" in ${violation.file}. ` +
        `Move it to a colocated types.ts (the project convention) instead of ` +
        `declaring it inline in a component/hook file.`,
    );
  }

  if (distinctCount > baselineCount) {
    errors.push(
      `Inline component/hook type count rose to ${distinctCount} ` +
        `(baseline ceiling ${baselineCount}). New inline declarations are not allowed.`,
    );
  }

  if (errors.length > 0) {
    process.stderr.write("\nComponent-type-location check FAILED:\n");
    for (const error of errors) {
      process.stderr.write(`  - ${error}\n`);
    }
    process.stderr.write(
      `\nNew inline component/hook types must be moved to a colocated types.ts ` +
        `(do NOT add them to the baseline). ${REGEN_HINT}\n`,
    );
    process.exit(1);
  }

  process.stdout.write(
    `Component-type-location check OK: ${distinctCount} grandfathered inline ` +
      `declaration(s), baseline ceiling ${baselineCount}, 0 new.\n`,
  );
}

main();
