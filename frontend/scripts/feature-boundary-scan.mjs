/**
 * Cross-context import scanner shared by the boundary checker and the baseline
 * generator, so both compute violations identically.
 *
 * Covers (AE-0083 + AE-0136):
 *   - the `features` owner layer: a feature must not import another feature's
 *     internals (`@/features/<other>/...`);
 *   - the `modules` owner layer: a module must not reach past another module's
 *     PUBLIC CONTRACT — i.e. `@/modules/<other>/<internal>` is forbidden, while
 *     the barrel `@/modules/<other>` (or `.../index`) is allowed; a module may
 *     freely import its OWN internals;
 *   - the MODULE PUBLIC-CONTRACT rule applies to EVERY layer (modules, app, and
 *     `features`): during the migration window a feature will import from
 *     modules, so a deep `@/modules/<m>/<internal>` import from ANY scanned file
 *     is a violation regardless of which layer it lives in. The barrel
 *     `@/modules/<m>` (or `.../index`) is always allowed.
 *   - the `app` consumer layer: `src/app` owns no context but may import a
 *     module's public contract only — `@/modules/<m>/<internal>` from `app/`
 *     is a violation.
 *
 * Owner-layer roots, import prefixes and owning-context derivation are
 * parameterized via `OWNER_LAYERS` / `APP_CONSUMER` in the config; nothing is
 * hardcoded to `src/features` anymore.
 */

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join, relative, sep } from "node:path";

import {
  APP_CONSUMER,
  EXCLUDE_PATTERNS,
  MODULE_IMPORT_PREFIX,
  OWNER_LAYERS,
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
 * @returns {string[]} absolute file paths (empty if the dir does not exist)
 */
function walkSourceFiles(dir) {
  if (!existsSync(dir)) {
    return [];
  }
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
 * Top-level context segment for a file living under an owner layer's `relDir`.
 *
 * @param {string} relPosixPath e.g. `src/modules/publishing/x.ts`
 * @param {string} layerRelDir  e.g. `src/modules`
 * @returns {string} e.g. `publishing`
 */
function contextOfFile(relPosixPath, layerRelDir) {
  return relPosixPath.slice(layerRelDir.length + 1).split("/")[0];
}

/**
 * Top-level context segment referenced by a `<prefix><context>/...` import.
 *
 * @param {string} specifier
 * @param {string} importPrefix
 * @returns {string}
 */
function contextOfImport(specifier, importPrefix) {
  return specifier.slice(importPrefix.length).split("/")[0];
}

/**
 * Whether a `@/modules/<X>/...` specifier targets the PUBLIC CONTRACT barrel
 * (`@/modules/<X>` or `@/modules/<X>/index`) rather than an internal path.
 *
 * @param {string} specifier
 * @returns {boolean}
 */
function isModuleBarrelSpecifier(specifier) {
  const rest = specifier.slice(MODULE_IMPORT_PREFIX.length); // `<X>` or `<X>/<...>`
  const [, ...deep] = rest.split("/");
  if (deep.length === 0) {
    return true; // `@/modules/<X>`
  }
  return deep.length === 1 && (deep[0] === "" || deep[0] === "index");
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
 * @property {string} from       importing file's context (or `app` for the consumer)
 * @property {string} to         imported (foreign) context
 * @property {string} specifier  the offending import specifier
 * @property {string} layer      owner-layer / consumer name producing the violation
 */

/**
 * For a `publicContract` owner layer (modules): a cross-context violation is any
 * DEEP import past another module's barrel. Importing a module's own internals,
 * or another module's public barrel, is allowed.
 *
 * @param {string} specifier
 * @param {string} fileContext
 * @returns {string|null} foreign context name if violating, else null
 */
function moduleInternalReach(specifier, fileContext) {
  if (!specifier.startsWith(MODULE_IMPORT_PREFIX)) {
    return null;
  }
  if (isModuleBarrelSpecifier(specifier)) {
    return null; // public contract — always allowed
  }
  const target = contextOfImport(specifier, MODULE_IMPORT_PREFIX);
  if (!target || target === fileContext) {
    return null; // own internals are allowed
  }
  return target; // deep reach into another module's internals
}

/**
 * For a non-publicContract owner layer (features): a cross-context violation is
 * any `@/<layer>/<other>/...` import where `<other>` differs from the file's
 * context.
 *
 * @param {string} specifier
 * @param {string} importPrefix
 * @param {string} fileContext
 * @returns {string|null} foreign context name if violating, else null
 */
function featureCrossImport(specifier, importPrefix, fileContext) {
  if (!specifier.startsWith(importPrefix)) {
    return null;
  }
  const target = contextOfImport(specifier, importPrefix);
  if (!target || target === fileContext) {
    return null;
  }
  return target;
}

/**
 * Resolve the cross-context violation (if any) for one specifier from a file in
 * the given owner layer. The MODULE PUBLIC-CONTRACT rule (deep `@/modules/<m>/
 * <internal>` reach) is enforced for EVERY layer; additionally, a non-public-
 * contract owner layer (features) enforces its own cross-context rule
 * (`@/features/<other>/...`). A `publicContract` layer (modules) is governed
 * solely by the module-reach rule (which also exempts a module's own internals).
 *
 * @param {string} specifier
 * @param {import("./feature-boundary.config.mjs").OwnerLayer} layer
 * @param {string} fileContext
 * @returns {{ to: string, layer: string }|null}
 */
function ownerLayerViolation(specifier, layer, fileContext) {
  const moduleReachContext = layer.publicContract ? fileContext : "";
  const moduleTarget = moduleInternalReach(specifier, moduleReachContext);
  if (moduleTarget) {
    return { to: moduleTarget, layer: "modules" };
  }
  if (layer.publicContract) {
    return null;
  }
  const crossTarget = featureCrossImport(
    specifier,
    layer.importPrefix,
    fileContext,
  );
  return crossTarget ? { to: crossTarget, layer: layer.name } : null;
}

/**
 * Scan one owner layer for cross-context internal imports.
 *
 * @param {import("./feature-boundary.config.mjs").OwnerLayer} layer
 * @returns {Violation[]}
 */
function scanOwnerLayer(layer) {
  /** @type {Violation[]} */
  const violations = [];
  for (const absPath of walkSourceFiles(layer.dir)) {
    const relPath = toRelativePosix(absPath);
    const fileContext = contextOfFile(relPath, layer.relDir);
    const content = readFileSync(absPath, "utf8");
    for (const specifier of extractSpecifiers(content)) {
      const result = ownerLayerViolation(specifier, layer, fileContext);
      if (result) {
        violations.push({
          file: relPath,
          from: fileContext,
          to: result.to,
          specifier,
          layer: result.layer,
        });
      }
    }
  }
  return violations;
}

/**
 * Scan the `app` consumer layer: it may import module PUBLIC CONTRACTS only, so
 * a deep `@/modules/<m>/<internal>` import is a violation.
 *
 * @returns {Violation[]}
 */
function scanAppConsumer() {
  /** @type {Violation[]} */
  const violations = [];
  for (const absPath of walkSourceFiles(APP_CONSUMER.dir)) {
    const relPath = toRelativePosix(absPath);
    const content = readFileSync(absPath, "utf8");
    for (const specifier of extractSpecifiers(content)) {
      // app owns no context, so any deep module reach is forbidden.
      const target = moduleInternalReach(specifier, /* fileContext */ "");
      if (target) {
        violations.push({
          file: relPath,
          from: APP_CONSUMER.name,
          to: target,
          specifier,
          layer: APP_CONSUMER.name,
        });
      }
    }
  }
  return violations;
}

/**
 * Scan every owner layer plus the app consumer and return all cross-context
 * internal / public-contract violations.
 *
 * @returns {Violation[]} sorted deterministically by file then specifier
 */
export function scanCrossFeatureImports() {
  /** @type {Violation[]} */
  const violations = [];
  for (const layer of OWNER_LAYERS) {
    violations.push(...scanOwnerLayer(layer));
  }
  violations.push(...scanAppConsumer());
  violations.sort(
    (a, b) =>
      a.file.localeCompare(b.file) || a.specifier.localeCompare(b.specifier),
  );
  return violations;
}

/**
 * Build the stable allowlist key for a violation: `<file>::<to-context>`.
 * Keyed by importing file + foreign context so adding a NEW foreign context to
 * an already-grandfathered file is still caught as a new violation. This format
 * is backward-compatible with the AE-0083 baseline (`src/features/X/file::Y`).
 *
 * @param {Violation} violation
 * @returns {string}
 */
export function violationKey(violation) {
  return `${violation.file}::${violation.to}`;
}
