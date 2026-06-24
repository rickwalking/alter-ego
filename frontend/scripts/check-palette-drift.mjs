#!/usr/bin/env node
/**
 * Palette-drift check (AE-0266 Phase 3, retargeted by AE-0271).
 *
 * The backend palette registry is the single source of truth. The generator
 * `backend/scripts/export_palettes.py` projects it to the committed contract
 * `docs/contracts/palettes.json`.
 *
 * History: this gate originally also diffed the create-form theme keys, label
 * keys, light-theme set, and i18n labels against the contract. AE-0271 made the
 * theme dropdown render the live `GET /api/palettes` catalog (roots + custom),
 * so those FE constants no longer exist — the API IS the source for them and a
 * static gate can't (and shouldn't) check a runtime list. The gate therefore
 * NARROWS to the one surface that is still hardcoded in the frontend and must
 * stay in lockstep with the backend: the supported `IMAGE_PRESETS` (model,
 * style) combos. The provider/style matrix is provider-tied, not user-editable,
 * so a drift there is still a real, just-introduced desync.
 *
 * It reports DRIFT when:
 *   - the create-form `IMAGE_PRESETS` (model__style) combos differ from the
 *     contract `image_presets`.
 *
 * BLOCKING from day one: the registry is in sync now, so any drift is a real,
 * just-introduced desync. Dependency-free static scan.
 *
 * Usage:
 *   node scripts/check-palette-drift.mjs            # advisory report (exit 0)
 *   node scripts/check-palette-drift.mjs --strict   # exit 1 on drift (CI)
 *
 * Path overrides (used by the rule-fires test to point at seeded fixtures):
 *   PALETTE_CONTRACT_PATH, CREATE_TS_PATH
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const FRONTEND_ROOT = join(fileURLToPath(new URL(".", import.meta.url)), "..");
const REPO_ROOT = join(FRONTEND_ROOT, "..");

const CONTRACT_PATH =
  process.env.PALETTE_CONTRACT_PATH ??
  join(REPO_ROOT, "docs/contracts/palettes.json");
const CREATE_TS_PATH =
  process.env.CREATE_TS_PATH ?? join(FRONTEND_ROOT, "src/constants/create.ts");

/**
 * Extract the body between `const NAME[: type] = <open>` and its matching close.
 */
function extractBlock(source, name, open, close) {
  const nameIdx = source.indexOf(`${name}`);
  if (nameIdx === -1) return null;
  const eqIdx = source.indexOf("=", nameIdx + name.length);
  if (eqIdx === -1) return null;
  const openIdx = source.indexOf(open, eqIdx);
  if (openIdx === -1) return null;
  let depth = 0;
  for (let i = openIdx; i < source.length; i += 1) {
    if (source[i] === open) depth += 1;
    else if (source[i] === close) {
      depth -= 1;
      if (depth === 0) return source.slice(openIdx + 1, i);
    }
  }
  return null;
}

/** Parse IMAGE_PRESETS `value: "model__style"` entries into [model__style]. */
function parseImagePresets(source) {
  const body = extractBlock(source, "IMAGE_PRESETS", "[", "]");
  const combos = [];
  if (body === null) return combos;
  const re = /value:\s*"([^"]+)__([^"]+)"/g;
  let m;
  while ((m = re.exec(body)) !== null) combos.push(`${m[1]}__${m[2]}`);
  return combos;
}

function setDiff(actual, expected, label, lines) {
  const a = new Set(actual);
  const e = new Set(expected);
  const missing = [...e].filter((x) => !a.has(x));
  const extra = [...a].filter((x) => !e.has(x));
  if (missing.length)
    lines.push(`  DRIFT ${label}: missing ${missing.join(", ")}`);
  if (extra.length)
    lines.push(`  DRIFT ${label}: unexpected ${extra.join(", ")}`);
  return missing.length + extra.length;
}

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function main() {
  const strict = process.argv.includes("--strict");

  let contract;
  let createSrc;
  try {
    contract = readJson(CONTRACT_PATH);
    createSrc = readFileSync(CREATE_TS_PATH, "utf8");
  } catch (err) {
    process.stderr.write(
      `Cannot run palette-drift check: ${err.message}\n` +
        "Generate the contract with `uv run python backend/scripts/export_palettes.py`.\n",
    );
    process.exit(strict ? 1 : 0);
  }

  const contractPresets = contract.image_presets.map(
    (p) => `${p.model}__${p.style}`,
  );
  const presets = parseImagePresets(createSrc);

  const lines = [];
  const drift = setDiff(
    presets,
    contractPresets,
    "IMAGE_PRESETS combos",
    lines,
  );

  process.stdout.write("\nPalette-drift report (AE-0266 Phase 3, AE-0271)\n");
  process.stdout.write(`  contract: ${CONTRACT_PATH}\n`);
  process.stdout.write(
    `  image presets: ${contractPresets.length} (theme list is now dynamic via GET /api/palettes)\n\n`,
  );
  if (drift === 0) {
    process.stdout.write(
      "  OK   create.ts IMAGE_PRESETS match the palette contract.\n",
    );
    process.exit(0);
  }
  process.stdout.write(`${lines.join("\n")}\n\n`);
  process.stdout.write(`${drift} palette-drift finding(s).\n`);
  if (strict) {
    process.stderr.write(
      "\nSTRICT mode: failing on drift. Reconcile the IMAGE_PRESETS in\n" +
        "src/constants/create.ts with docs/contracts/palettes.json (regenerate it\n" +
        "via `uv run python backend/scripts/export_palettes.py` if the backend changed).\n",
    );
    process.exit(1);
  }
  process.exit(0);
}

main();
