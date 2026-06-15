/**
 * Cross-feature import scanner shared by the boundary checker and the
 * baseline generator, so both compute violations identically.
 *
 * See AE-0083. Scaffolding only — no behavior change.
 */

import { readFileSync, readdirSync } from "node:fs";
import { join, relative, sep } from "node:path";

import {
  EXCLUDE_PATTERNS,
  FEATURES_DIR,
  FEATURE_IMPORT_PREFIX,
  ROOT,
  SOURCE_EXTENSIONS,
} from "./feature-boundary.config.mjs";

/**
 * Matches static `import ... from "<spec>"`, side-effect `import "<spec>"`,
 * `export ... from "<spec>"`, and dynamic `import("<spec>")` specifiers.
 */
const IMPORT_SPECIFIER_RE =
  /(?:import|export)\b[^'"]*?from\s*['"]([^'"]+)['"]|import\s*['"]([^'"]+)['"]|import\s*\(\s*['"]([^'"]+)['"]\s*\)/g;

/**
 * @param {string} fileName
 * @returns {boolean}
 */
function isExcluded(fileName) {
  return EXCLUDE_PATTERNS.some((pattern) => fileName.includes(pattern));
}

/**
 * @param {string} dir
 * @returns {string[]} absolute file paths
 */
function walkSourceFiles(dir) {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walkSourceFiles(full));
      continue;
    }
    if (isExcluded(entry.name)) {
      continue;
    }
    if (SOURCE_EXTENSIONS.some((ext) => entry.name.endsWith(ext))) {
      out.push(full);
    }
  }
  return out;
}

/**
 * Convert an absolute path to a POSIX, ROOT-relative path for stable keys
 * across platforms and machines.
 *
 * @param {string} absPath
 * @returns {string}
 */
export function toRelativePosix(absPath) {
  return relative(ROOT, absPath).split(sep).join("/");
}

/**
 * Top-level feature segment for a file living under `src/features/`.
 *
 * @param {string} relPosixPath e.g. `src/features/dashboard/workflow/x.ts`
 * @returns {string} e.g. `dashboard`
 */
function featureOfFile(relPosixPath) {
  return relPosixPath.split("/")[2];
}

/**
 * Top-level feature segment referenced by a `@/features/<feature>/...` import.
 *
 * @param {string} specifier
 * @returns {string}
 */
function featureOfImport(specifier) {
  return specifier.slice(FEATURE_IMPORT_PREFIX.length).split("/")[0];
}

/**
 * @param {string} content
 * @returns {string[]} all import/export specifiers found in the file
 */
function extractSpecifiers(content) {
  const specifiers = [];
  for (const match of content.matchAll(IMPORT_SPECIFIER_RE)) {
    const spec = match[1] ?? match[2] ?? match[3];
    if (spec) {
      specifiers.push(spec);
    }
  }
  return specifiers;
}

/**
 * @typedef {object} Violation
 * @property {string} file       ROOT-relative POSIX path of the importing file
 * @property {string} from       importing file's feature
 * @property {string} to         imported (foreign) feature
 * @property {string} specifier  the offending import specifier
 */

/**
 * Scan all feature source files and return every cross-feature internal import.
 *
 * @returns {Violation[]} sorted deterministically by file then specifier
 */
export function scanCrossFeatureImports() {
  /** @type {Violation[]} */
  const violations = [];
  for (const absPath of walkSourceFiles(FEATURES_DIR)) {
    const relPath = toRelativePosix(absPath);
    const fileFeature = featureOfFile(relPath);
    const content = readFileSync(absPath, "utf8");
    for (const specifier of extractSpecifiers(content)) {
      if (!specifier.startsWith(FEATURE_IMPORT_PREFIX)) {
        continue;
      }
      const importFeature = featureOfImport(specifier);
      if (importFeature && importFeature !== fileFeature) {
        violations.push({
          file: relPath,
          from: fileFeature,
          to: importFeature,
          specifier,
        });
      }
    }
  }
  violations.sort(
    (a, b) =>
      a.file.localeCompare(b.file) || a.specifier.localeCompare(b.specifier),
  );
  return violations;
}

/**
 * Build the stable allowlist key for a violation: `<file>::<to-feature>`.
 * Keyed by importing file + foreign feature so adding a NEW foreign feature
 * to an already-grandfathered file is still caught as a new violation.
 *
 * @param {Violation} violation
 * @returns {string}
 */
export function violationKey(violation) {
  return `${violation.file}::${violation.to}`;
}
