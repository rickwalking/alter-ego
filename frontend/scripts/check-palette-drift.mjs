#!/usr/bin/env node
/**
 * Palette-drift check (AE-0266 Phase 3).
 *
 * The backend palette registry is the single source of truth. The generator
 * `backend/scripts/export_palettes.py` projects it to the committed contract
 * `docs/contracts/palettes.json`. This gate diffs the create-form constants and
 * the i18n locale labels against that contract so the theme dropdown, the zod
 * preset combos, and the locale labels can no longer silently desync from the
 * backend — the "FE missed a new theme" class of the AE-0264 bugs.
 *
 * It reports DRIFT when:
 *   - the create-form theme keys (CAROUSEL_THEMES, minus the FE-only `auto`
 *     sentinel) differ from the contract themes,
 *   - THEME_LABEL_KEYS does not cover exactly the CAROUSEL_THEMES keys,
 *   - LIGHT_THEME_KEYS differs from the contract light_theme_keys,
 *   - the IMAGE_PRESETS (model, style) combos differ from the contract presets,
 *   - an i18n label (en/pt) is missing or differs from the contract label.
 *
 * BLOCKING from day one (unlike schema-drift): the registry is in sync now, so
 * any drift is a real, just-introduced desync. Dependency-free static scan, in
 * the style of the other gate scripts (url-inventory, schema-drift).
 *
 * Usage:
 *   node scripts/check-palette-drift.mjs            # advisory report (exit 0)
 *   node scripts/check-palette-drift.mjs --strict   # exit 1 on drift (CI)
 *
 * Path overrides (used by the rule-fires test to point at seeded fixtures):
 *   PALETTE_CONTRACT_PATH, CREATE_TS_PATH, I18N_EN_PATH, I18N_PT_PATH
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
const I18N_EN_PATH =
  process.env.I18N_EN_PATH ?? join(FRONTEND_ROOT, "src/i18n/locales/en.json");
const I18N_PT_PATH =
  process.env.I18N_PT_PATH ?? join(FRONTEND_ROOT, "src/i18n/locales/pt.json");

/** The one sanctioned FE-only theme option: "let the backend auto-detect". */
const FE_ONLY_THEME_SENTINEL = "auto";

/**
 * Extract the body between `const NAME[: type] = <open>` and its matching close.
 *
 * Keys on the assignment `=` after the name (not on `NAME =` adjacency) so a
 * type annotation such as `: readonly string[]` — whose own brackets would
 * otherwise be mistaken for the array literal — is skipped before scanning.
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

/** Map of `IDENT: "value"` object entries (e.g. CAROUSEL_THEMES). */
function parseIdentToValue(source, name) {
  const body = extractBlock(source, name, "{", "}");
  const map = new Map();
  if (body === null) return map;
  const re = /([A-Za-z0-9_]+)\s*:\s*"([^"]+)"/g;
  let m;
  while ((m = re.exec(body)) !== null) map.set(m[1], m[2]);
  return map;
}

/** Resolve `CAROUSEL_THEMES.RISOGRAPH` references inside an array literal. */
function parseLightThemeKeys(source, themeMap) {
  const body = extractBlock(source, "LIGHT_THEME_KEYS", "[", "]");
  const keys = [];
  if (body === null) return keys;
  const re = /CAROUSEL_THEMES\.([A-Za-z0-9_]+)/g;
  let m;
  while ((m = re.exec(body)) !== null) {
    const value = themeMap.get(m[1]);
    if (value) keys.push(value);
  }
  return keys;
}

/** Parse IMAGE_PRESETS `value: "model__style"` entries into [model, style]. */
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

function checkLabels(themes, locale, localeName, lines) {
  let drift = 0;
  const table = locale?.create?.themes ?? {};
  for (const theme of themes) {
    const want = localeName === "en" ? theme.label_en : theme.label_pt;
    const got = table[theme.key];
    if (got === undefined) {
      lines.push(
        `  DRIFT i18n.${localeName}: theme "${theme.key}" has no label`,
      );
      drift += 1;
    } else if (got !== want) {
      lines.push(
        `  DRIFT i18n.${localeName}: "${theme.key}" is "${got}", contract says "${want}"`,
      );
      drift += 1;
    }
  }
  if (table[FE_ONLY_THEME_SENTINEL] === undefined) {
    lines.push(
      `  DRIFT i18n.${localeName}: missing "${FE_ONLY_THEME_SENTINEL}" label`,
    );
    drift += 1;
  }
  return drift;
}

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function main() {
  const strict = process.argv.includes("--strict");

  let contract;
  let createSrc;
  let en;
  let pt;
  try {
    contract = readJson(CONTRACT_PATH);
    createSrc = readFileSync(CREATE_TS_PATH, "utf8");
    en = readJson(I18N_EN_PATH);
    pt = readJson(I18N_PT_PATH);
  } catch (err) {
    process.stderr.write(
      `Cannot run palette-drift check: ${err.message}\n` +
        "Generate the contract with `uv run python backend/scripts/export_palettes.py`.\n",
    );
    process.exit(strict ? 1 : 0);
  }

  const contractThemeKeys = contract.themes.map((t) => t.key);
  const contractPresets = contract.image_presets.map(
    (p) => `${p.model}__${p.style}`,
  );

  const themeMap = parseIdentToValue(createSrc, "CAROUSEL_THEMES");
  const feThemeValues = [...themeMap.values()].filter(
    (v) => v !== FE_ONLY_THEME_SENTINEL,
  );
  const labelKeys = [
    ...parseIdentToValue(createSrc, "THEME_LABEL_KEYS").keys(),
  ];
  const lightKeys = parseLightThemeKeys(createSrc, themeMap);
  const presets = parseImagePresets(createSrc);

  const lines = [];
  let drift = 0;
  drift += setDiff(
    feThemeValues,
    contractThemeKeys,
    "themes (CAROUSEL_THEMES)",
    lines,
  );
  drift += setDiff(
    labelKeys,
    [...themeMap.values()],
    "THEME_LABEL_KEYS coverage",
    lines,
  );
  drift += setDiff(
    lightKeys,
    contract.light_theme_keys,
    "LIGHT_THEME_KEYS",
    lines,
  );
  drift += setDiff(presets, contractPresets, "IMAGE_PRESETS combos", lines);
  drift += checkLabels(contract.themes, en, "en", lines);
  drift += checkLabels(contract.themes, pt, "pt", lines);

  process.stdout.write("\nPalette-drift report (AE-0266 Phase 3)\n");
  process.stdout.write(`  contract: ${CONTRACT_PATH}\n`);
  process.stdout.write(
    `  themes: ${contractThemeKeys.length}  presets: ${contractPresets.length}\n\n`,
  );
  if (drift === 0) {
    process.stdout.write(
      "  OK   create.ts + i18n match the palette contract.\n",
    );
    process.exit(0);
  }
  process.stdout.write(`${lines.join("\n")}\n\n`);
  process.stdout.write(`${drift} palette-drift finding(s).\n`);
  if (strict) {
    process.stderr.write(
      "\nSTRICT mode: failing on drift. Reconcile src/constants/create.ts + i18n\n" +
        "locales with docs/contracts/palettes.json (regenerate it via\n" +
        "`uv run python backend/scripts/export_palettes.py` if the backend changed).\n",
    );
    process.exit(1);
  }
  process.exit(0);
}

main();
