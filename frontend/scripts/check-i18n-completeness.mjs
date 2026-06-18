#!/usr/bin/env node
/**
 * AE-0214 — i18n completeness lint: every statically-referenced translation key
 * must exist in EVERY locale.
 *
 * Background: `create.preview.previousSlide` / `create.preview.nextSlide` were
 * referenced by create-carousel-preview.tsx via `useTranslations("create")` +
 * `t("preview.previousSlide")`, but the locale JSON only carried them under
 * `publish.carouselViewer.*` — so prod rendered the raw keys on the nav buttons
 * and logged next-intl `MISSING_MESSAGE` errors. No lint caught it. This guard
 * does, statically, as part of `npm run lint`.
 *
 * How it resolves keys (dependency-free, no AST):
 *   1. Find each `const <alias> = [await] (useTranslations|getTranslations)("<ns>")`
 *      declaration and bind <alias> -> <ns> per file.
 *   2. Find each `<alias>("<literal>")` (and `.rich/.raw/.markup/.has("<literal>")`)
 *      call with a STATIC string-literal first arg; resolve full key = `<ns>.<key>`.
 *   3. A key is a violation if it is absent from ANY locale.
 *
 * Dynamic keys (template literals `t(`a.${x}`)` or variables `t(key)`) are NOT
 * statically resolvable and are skipped — that is the legitimate dynamic-key
 * case. If a specific full key must be exempted, add it (with a justification)
 * to i18n-completeness-allowlist.json.
 *
 * Run as part of `npm run lint` (and standalone `npm run lint:i18n`).
 *
 * Env (for tests): I18N_SCAN_ROOT overrides the src scan root (default "src");
 *   I18N_LOCALES_DIR overrides the locales dir (default "src/i18n/locales");
 *   I18N_ALLOWLIST overrides the allow-list JSON path.
 */
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const FRONTEND_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SCAN_ROOT = process.env.I18N_SCAN_ROOT || join(FRONTEND_ROOT, "src");
const LOCALES_DIR =
  process.env.I18N_LOCALES_DIR || join(FRONTEND_ROOT, "src/i18n/locales");
const DEFAULT_ALLOWLIST = join(
  FRONTEND_ROOT,
  "i18n-completeness-allowlist.json",
);

// `const t = useTranslations("ns")` / `const t = await getTranslations("ns")`.
// Captures alias (group 1) and namespace (group 2). Namespace must be a string
// literal — `getTranslations({ locale, namespace })` object form is skipped
// (no usable static namespace).
const HOOK_DECL_RE =
  /\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:await\s+)?(?:useTranslations|getTranslations)\s*\(\s*["'`]([^"'`]+)["'`]\s*\)/g;

// Block + line comment stripper (shared idiom with check-use-client.mjs) so a
// `t("x")` mentioned only in a comment is not treated as a real reference.
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:'"`])\/\/.*$/gm, "$1");
}

function walk(dir, out = []) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name.startsWith(".")) continue;
    const p = join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(p, out);
    } else if (
      /\.(ts|tsx)$/.test(p) &&
      !/\.(test|spec|stories)\.(ts|tsx)$/.test(p)
    ) {
      out.push(p);
    }
  }
  return out;
}

/** Flatten a nested locale object into a Set of dotted leaf keys. */
function flattenKeys(obj, prefix = "", out = new Set()) {
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object" && !Array.isArray(v)) {
      flattenKeys(v, path, out);
    } else {
      out.add(path);
    }
  }
  return out;
}

function loadLocales() {
  const files = readdirSync(LOCALES_DIR).filter((f) => f.endsWith(".json"));
  if (files.length === 0) {
    throw new Error(`No locale JSON files found in ${LOCALES_DIR}`);
  }
  const locales = {};
  for (const file of files) {
    const name = file.replace(/\.json$/, "");
    const parsed = JSON.parse(readFileSync(join(LOCALES_DIR, file), "utf8"));
    locales[name] = flattenKeys(parsed);
  }
  return locales;
}

function loadAllowlist() {
  const path = process.env.I18N_ALLOWLIST ?? DEFAULT_ALLOWLIST;
  if (!existsSync(path)) return new Set();
  const parsed = JSON.parse(readFileSync(path, "utf8"));
  return new Set(Object.keys(parsed.allow ?? {}));
}

/**
 * Collect static full-key references from one file's source.
 * @returns {Array<{key: string, file: string}>}
 */
function collectReferences(file) {
  const code = stripComments(readFileSync(file, "utf8"));
  const aliasToNs = new Map();
  for (const m of code.matchAll(HOOK_DECL_RE)) {
    aliasToNs.set(m[1], m[2]);
  }
  if (aliasToNs.size === 0) return [];

  const refs = [];
  for (const [alias, ns] of aliasToNs) {
    // `alias("literal")` or `alias.rich/.raw/.markup/.has("literal")`. The first
    // arg MUST be a plain string literal (no template literals / variables) —
    // dynamic keys are intentionally skipped.
    const callRe = new RegExp(
      String.raw`\b${alias}(?:\.(?:rich|raw|markup|has))?\s*\(\s*["']([^"']+)["']`,
      "g",
    );
    for (const m of code.matchAll(callRe)) {
      refs.push({ key: `${ns}.${m[1]}`, file });
    }
  }
  return refs;
}

function main() {
  const locales = loadLocales();
  const localeNames = Object.keys(locales);
  const allow = loadAllowlist();
  const files = walk(SCAN_ROOT);

  /** @type {Map<string, {key: string, file: string, missingIn: string[]}>} */
  const violations = new Map();
  let refCount = 0;

  for (const file of files) {
    for (const ref of collectReferences(file)) {
      refCount += 1;
      if (allow.has(ref.key)) continue;
      const missingIn = localeNames.filter((l) => !locales[l].has(ref.key));
      if (missingIn.length === 0) continue;
      const existing = violations.get(ref.key);
      if (existing) {
        if (!existing.file.includes(ref.file)) existing.file += `, ${ref.file}`;
      } else {
        violations.set(ref.key, { key: ref.key, file: ref.file, missingIn });
      }
    }
  }

  if (violations.size > 0) {
    process.stderr.write(
      `\ni18n completeness check FAILED (AE-0214): ${violations.size} ` +
        `referenced key(s) missing from at least one locale ` +
        `(${localeNames.join(", ")}):\n\n`,
    );
    for (const v of violations.values()) {
      process.stderr.write(
        `  ✗ "${v.key}" — missing in [${v.missingIn.join(", ")}]\n` +
          `      referenced by ${v.file}\n`,
      );
    }
    process.stderr.write(
      `\nFix: add the key to every locale under ${LOCALES_DIR}, or — for a\n` +
        `legitimate dynamic-key case — add the full key (with a justification)\n` +
        `to i18n-completeness-allowlist.json.\n`,
    );
    process.exit(1);
  }

  process.stdout.write(
    `i18n completeness OK: ${refCount} static key reference(s) across ` +
      `${files.length} file(s); all present in ${localeNames.length} locale(s) ` +
      `(${localeNames.join(", ")}).\n`,
  );
}

main();
