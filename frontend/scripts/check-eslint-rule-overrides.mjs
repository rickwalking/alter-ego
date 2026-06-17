#!/usr/bin/env node
/**
 * AE-0179 — guard against the ESLint flat-config "replace-not-merge" footgun.
 *
 * In flat config, when two config objects both set the same rule key and both
 * match a file, the LATER object's value REPLACES the earlier — arrays are NOT
 * merged. During AE-0166 a scoped `no-restricted-syntax` *warn* block silently
 * overrode the global fetch-in-useEffect *error* in src/modules/src/components,
 * so the flagship rule was unenforced exactly where it mattered. It shipped green
 * and was only caught by an adversarial reviewer (finding H1).
 *
 * This guard FAILS when the SAME rule key is declared by more than one LOCAL
 * config object (objects authored in eslint.config.mjs — preset spreads from
 * eslint-config-next are excluded, since overriding a preset is the documented,
 * intended customization mechanism) whose `files` globs can OVERLAP, UNLESS the
 * rule is listed in eslint-rule-override-allowlist.json with a justification.
 *
 * Overlap-aware (not a naive any-duplicate check): two objects only collide if a
 * real file path could be matched by BOTH (respecting each object's `ignores`).
 * The test-file block re-declares e.g. `no-non-null-assertion` to turn it off;
 * that overlaps the global object, so without the allow-list it would false-
 * positive — which is exactly why the allow-list exists and is seeded with the
 * current intentional re-declares.
 *
 * Run as part of `npm run lint` (and standalone `npm run lint:eslint-overrides`).
 *
 * Env (for the rule-fires test): ESLINT_OVERRIDE_CONFIG points at an alternate
 * config module to load instead of ./eslint.config.mjs; ESLINT_OVERRIDE_ALLOWLIST
 * points at an alternate allow-list JSON.
 */

import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import micromatch from "micromatch";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const FRONTEND_ROOT = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "..",
);
const DEFAULT_CONFIG = resolve(FRONTEND_ROOT, "eslint.config.mjs");
const DEFAULT_ALLOWLIST = resolve(
  FRONTEND_ROOT,
  "eslint-rule-override-allowlist.json",
);

// Representative probe paths spanning the real src/ structure + the special
// scopes (pages, lib, hooks, modules, constants, schemas, tests). Overlap is
// detected if any single probe is matched by two objects setting the same key.
const PROBE_PATHS = [
  "src/app/page.tsx",
  "src/app/x/page.tsx",
  "src/app/x/route.ts",
  "src/components/a.tsx",
  "src/components/a.ts",
  "src/lib/u.ts",
  "src/lib/u.tsx",
  "src/features/f/helpers.ts",
  "src/features/f/x.ts",
  "src/modules/m/hooks/use-x.ts",
  "src/modules/m/hooks/use-x.tsx",
  "src/modules/m/x.ts",
  "src/modules/m/x.tsx",
  "src/constants/c.ts",
  "src/schemas/s.ts",
  "src/foo.tsx",
  "src/foo.ts",
  "x.test.ts",
  "src/a.test.tsx",
  "tests/e.ts",
  "src/test/h.ts",
];

const MIN_OBJECTS_FOR_COLLISION = 2;

/** @param {unknown} v @returns {string[]} */
function asGlobList(v) {
  if (!v) return [];
  return (Array.isArray(v) ? v : [v]).flat(Infinity);
}

/**
 * Does a config object apply to `probe`? A null/absent `files` means it applies
 * globally; a matching `ignores` excludes it.
 * @param {{files?: unknown, ignores?: unknown}} obj
 * @param {string} probe
 */
function applies(obj, probe) {
  const files = asGlobList(obj.files);
  const ignores = asGlobList(obj.ignores);
  const matched = files.length === 0 || micromatch.isMatch(probe, files);
  if (!matched) return false;
  if (ignores.length > 0 && micromatch.isMatch(probe, ignores)) return false;
  return true;
}

/** @returns {Record<string, string>} the allow map (rule -> justification). */
function loadAllowlist() {
  const path = process.env.ESLINT_OVERRIDE_ALLOWLIST ?? DEFAULT_ALLOWLIST;
  if (!existsSync(path)) return {};
  const parsed = JSON.parse(readFileSync(path, "utf8"));
  return parsed.allow ?? {};
}

async function loadLocalRuleObjects() {
  const configPath = process.env.ESLINT_OVERRIDE_CONFIG ?? DEFAULT_CONFIG;
  const mod = await import(pathToFileURL(configPath).href);
  const config = mod.default;
  if (!Array.isArray(config)) {
    throw new Error(`ESLint config at ${configPath} did not default-export an array.`);
  }
  // Preset objects (eslint-config-next spreads) are excluded by reference: a
  // local object overriding a preset is the intended flat-config mechanism.
  const presets = new Set([...nextVitals, ...nextTs]);
  return config.filter((o) => o && o.rules && !presets.has(o));
}

/**
 * @param {Array<{files?: unknown, ignores?: unknown, rules: Record<string, unknown>}>} objects
 * @returns {string[]} rule keys declared by >=2 objects sharing a matchable path.
 */
function findOverlappingDuplicateKeys(objects) {
  /** @type {Map<string, number[]>} */
  const byKey = new Map();
  objects.forEach((obj, idx) => {
    for (const key of Object.keys(obj.rules)) {
      if (!byKey.has(key)) byKey.set(key, []);
      byKey.get(key).push(idx);
    }
  });

  const overlapping = [];
  for (const [key, idxs] of byKey) {
    if (idxs.length < MIN_OBJECTS_FOR_COLLISION) continue;
    const overlaps = PROBE_PATHS.some(
      (probe) => idxs.filter((i) => applies(objects[i], probe)).length >= MIN_OBJECTS_FOR_COLLISION,
    );
    if (overlaps) overlapping.push(key);
  }
  return overlapping.sort();
}

async function main() {
  const objects = await loadLocalRuleObjects();
  const allow = loadAllowlist();
  const overlapping = findOverlappingDuplicateKeys(objects);

  const violations = overlapping.filter((key) => !(key in allow));

  if (violations.length > 0) {
    process.stderr.write(
      "\nESLint rule-override guard FAILED (AE-0179): rule key(s) declared in\n" +
        "more than one overlapping flat-config object. In flat config the LATER\n" +
        "object REPLACES the earlier value (no array merge), so one silently\n" +
        "neuters the other.\n\n",
    );
    for (const key of violations) {
      process.stderr.write(`  - "${key}"\n`);
    }
    process.stderr.write(
      "\nFix: collapse to a single declaration, or — if the re-declare is\n" +
        "intentional — add the rule to eslint-rule-override-allowlist.json with a\n" +
        "justification (this re-permits the footgun for that rule, so be sure).\n",
    );
    process.exit(1);
  }

  process.stdout.write(
    `ESLint rule-override guard OK: ${overlapping.length} overlapping re-declare(s), ` +
      `all allow-listed; 0 unlisted collisions.\n`,
  );
}

main().catch((err) => {
  process.stderr.write(`check-eslint-rule-overrides: ${err.message}\n`);
  process.exit(1);
});
