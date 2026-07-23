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

const BASELINE_PATH = new URL("./strict-index-baseline.json", import.meta.url);

const errorsByFile = collectStrictIndexErrors();
const files = Object.fromEntries(
  Object.entries(errorsByFile).sort(([a], [b]) => a.localeCompare(b)),
);
const { total } = evaluateStrictIndex(errorsByFile, { count: Infinity, files });

if (existsSync(BASELINE_PATH)) {
  const existing = JSON.parse(readFileSync(BASELINE_PATH, "utf8"));
  if (total > existing.count) {
    process.stderr.write(
      `REFUSED: new total (${total}) exceeds the committed baseline (${existing.count}).\n` +
        "The strict-index baseline is DOWN-ONLY — fix the new errors instead of absorbing them.\n",
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
