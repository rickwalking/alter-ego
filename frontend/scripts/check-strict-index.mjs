#!/usr/bin/env node
/**
 * noUncheckedIndexedAccess gate (AE-0324).
 *
 * Failure class (kaizen session-2026-07-22 FC-4 / the AE-0295 prod incident):
 * an unguarded `Record[key]` lookup destructured without a fallback crashed
 * the whole admin blog listing with a runtime TypeError. The flag makes the
 * class a compile error, but enabling it repo-wide today surfaces 76 legacy
 * errors — so this gate runs `tsc -p tsconfig.strict-index.json` (the flag ON
 * over the WHOLE tree) against a DOWN-ONLY per-file baseline:
 *
 *   - a file NOT in the baseline must have ZERO errors (every currently-clean
 *     file — including everything AE-0295 touched — is enforced immediately);
 *   - a baselined file must not EXCEED its recorded error count;
 *   - the TOTAL must not exceed the baseline count.
 *
 * Ratchet DOWN by fixing errors and running `npm run strict-index:baseline`
 * (the generator refuses to raise the count). When the baseline reaches 0,
 * delete it and fold `noUncheckedIndexedAccess` into tsconfig.json.
 *
 * Env (tests): STRICT_INDEX_PROJECT / STRICT_INDEX_BASELINE override paths.
 */

import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const FRONTEND_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const TSC_BIN = join(FRONTEND_ROOT, "node_modules", "typescript", "bin", "tsc");
const PROJECT_PATH =
  process.env.STRICT_INDEX_PROJECT ??
  join(FRONTEND_ROOT, "tsconfig.strict-index.json");
const BASELINE_PATH =
  process.env.STRICT_INDEX_BASELINE ??
  join(FRONTEND_ROOT, "scripts", "strict-index-baseline.json");
const REGEN_HINT =
  "Fix the errors, or ratchet DOWN with `npm run strict-index:baseline`.";

const ERROR_LINE_RE = /^(.+?)\(\d+,\d+\): error TS\d+/;

/**
 * Run tsc for the strict-index project and count errors per file.
 * @returns {Record<string, number>} posix-relative file -> error count
 */
export function collectStrictIndexErrors() {
  let output = "";
  try {
    execFileSync(process.execPath, [TSC_BIN, "-p", PROJECT_PATH], {
      cwd: dirname(PROJECT_PATH),
      encoding: "utf8",
      maxBuffer: 64 * 1024 * 1024,
    });
  } catch (err) {
    const e = /** @type {{ stdout?: string }} */ (err);
    output = e.stdout?.toString() ?? "";
    if (!output) {
      throw err;
    }
  }
  /** @type {Record<string, number>} */
  const byFile = {};
  for (const line of output.split("\n")) {
    const match = ERROR_LINE_RE.exec(line.trim());
    if (!match) {
      continue;
    }
    const file = match[1].replaceAll("\\", "/");
    byFile[file] = (byFile[file] ?? 0) + 1;
  }
  return byFile;
}

/**
 * Pure baseline comparison (exported for the AE-0180 rule-fires tests).
 * @param {Record<string, number>} errorsByFile
 * @param {{ count: number, files: Record<string, number> }} baseline
 * @returns {{ violations: string[], total: number }}
 */
export function evaluateStrictIndex(errorsByFile, baseline) {
  /** @type {string[]} */
  const violations = [];
  let total = 0;
  for (const [file, count] of Object.entries(errorsByFile)) {
    total += count;
    const allowed = baseline.files[file];
    if (allowed === undefined) {
      violations.push(
        `NEW: ${file} has ${count} unchecked-indexed-access error(s) but is not in the baseline (new files must be clean).`,
      );
      continue;
    }
    if (count > allowed) {
      violations.push(
        `GREW: ${file} has ${count} error(s), baseline allows ${allowed}.`,
      );
    }
  }
  if (total > baseline.count) {
    violations.push(
      `TOTAL: ${total} error(s) exceed the baseline count of ${baseline.count}.`,
    );
  }
  return { violations, total };
}

function main() {
  const baseline = JSON.parse(readFileSync(BASELINE_PATH, "utf8"));
  const errorsByFile = collectStrictIndexErrors();
  const { violations, total } = evaluateStrictIndex(errorsByFile, baseline);

  process.stdout.write(
    `noUncheckedIndexedAccess gate (AE-0324): ${total} error(s), baseline ${baseline.count}.\n`,
  );
  if (violations.length > 0) {
    process.stdout.write(
      `${violations.map((v) => `  - ${v}`).join("\n")}\n${REGEN_HINT}\n`,
    );
    process.exit(1);
  }
  if (total < baseline.count) {
    process.stdout.write(
      `Baseline can ratchet DOWN (${baseline.count} -> ${total}): run \`npm run strict-index:baseline\`.\n`,
    );
  }
  process.stdout.write("OK — no new unchecked indexed access.\n");
}

// endsWith (not fileURLToPath equality): vitest imports carry a non-file URL.
if (process.argv[1] && process.argv[1].endsWith("check-strict-index.mjs")) {
  main();
}
