#!/usr/bin/env node
/**
 * Regenerate the noUncheckedIndexedAccess baseline (AE-0324) — DOWN-ONLY.
 *
 * Refuses to write a baseline whose total EXCEEDS the committed one: the
 * baseline exists to shrink as legacy errors are fixed, never to absorb new
 * ones (raising it is gate-loosening; fix the new errors instead).
 */

import { existsSync, readFileSync, writeFileSync } from "node:fs";

import {
  collectStrictIndexErrors,
  evaluateStrictIndex,
} from "./check-strict-index.mjs";

// STRICT_INDEX_BASELINE override keeps the down-only tests hermetic (F-2).
const BASELINE_PATH =
  process.env.STRICT_INDEX_BASELINE ??
  new URL("./strict-index-baseline.json", import.meta.url);

const errorsByFile = collectStrictIndexErrors();
const files = Object.fromEntries(
  Object.entries(errorsByFile).sort(([a], [b]) => a.localeCompare(b)),
);
const { total } = evaluateStrictIndex(errorsByFile, { count: Infinity, files });

if (existsSync(BASELINE_PATH)) {
  const existing = JSON.parse(readFileSync(BASELINE_PATH, "utf8"));
  // DOWN-ONLY per FILE, not just per total (external QA F-2, 2026-07-23):
  // a total that shrinks can still hide a NEW or GROWN file's errors being
  // absorbed into the baseline — exactly the gaming the checker blocks.
  const { violations } = evaluateStrictIndex(errorsByFile, existing);
  if (violations.length > 0) {
    process.stderr.write(
      `REFUSED: the current tree violates the committed baseline — the generator\n` +
        `never absorbs NEW/GROWN/TOTAL violations (fix them instead):\n` +
        `${violations.map((v) => `  - ${v}`).join("\n")}\n`,
    );
    process.exit(1);
  }
}

writeFileSync(
  BASELINE_PATH,
  `${JSON.stringify({ count: total, files }, null, 2)}\n`,
  "utf8",
);
process.stdout.write(`strict-index baseline written: ${total} error(s) across ${Object.keys(files).length} file(s).\n`);
