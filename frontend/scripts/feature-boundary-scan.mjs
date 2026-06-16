/**
 * Cross-context import scanner shared by the boundary checker and the baseline
 * generator, so both compute violations identically.
 *
 * Covers, during the Phase 7 feature -> module migration window (AE-0136):
 *   - the legacy `features` barrel-less rule (AE-0083, broadened in AE-0138):
 *     `features` has NO public barrel, so ANY consumer (a `features/A/**` file,
 *     a `modules/<m>/**` file, or `app/`) importing `@/features/B/<anything>`
 *     of a DIFFERENT context B is a cross-context edge. A `features/A/**` file
 *     importing its OWN context A is allowed; a `modules` file importing
 *     `@/features/B` is ALWAYS cross-context (a module never owns a feature
 *     context). This closes the blind spot where former feature->feature edges
 *     "disappeared" merely because the source moved into `modules/`.
 *   - the `modules` public-contract rule: ANY consumer (a feature, `app/`, or
 *     ANOTHER module) must import a module's barrel (`@/modules/<m>` or
 *     `@/modules/<m>/index`), never a deep internal `@/modules/<m>/<internal>`;
 *     a module importing its OWN internals is allowed.
 *
 * The stable allowlist key stays `<file>::<to-context>` so the AE-0083 baseline
 * keys keep matching and regenerating it remains byte-identical.
 */

import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join, relative, sep } from "node:path";

import {
  APP_CONSUMER,
  EXCLUDE_PATTERNS,
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

/** Specifier suffix that denotes an explicit barrel import (still allowed). */
const INDEX_SUFFIX = "/index";

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
 * Owning context of a file inside an owner layer: the segment directly under the
 * layer's `relDir` (generic replacement for the old `split("/")[2]`).
 *
 * @param {string} relPosixPath e.g. `src/features/dashboard/workflow/x.ts`
 * @param {import("./feature-boundary.config.mjs").OwnerLayer} layer
 * @returns {string} e.g. `dashboard`
 */
function contextOfFile(relPosixPath, layer) {
  return relPosixPath.slice(`${layer.relDir}/`.length).split("/")[0];
}

/**
 * Top-level context segment referenced by a `<importPrefix><ctx>/...` import.
 *
 * @param {string} specifier
 * @param {import("./feature-boundary.config.mjs").OwnerLayer} layer
 * @returns {string}
 */
function contextOfImport(specifier, layer) {
  return specifier.slice(layer.importPrefix.length).split("/")[0];
}

/**
 * Whether `specifier` reaches a DEEP internal of `<importPrefix><ctx>` rather
 * than the public barrel. The bare prefix (`@/modules/m`) and the explicit
 * `@/modules/m/index` are barrel imports (allowed); anything deeper is internal.
 *
 * @param {string} specifier
 * @param {import("./feature-boundary.config.mjs").OwnerLayer} layer
 * @param {string} ctx
 * @returns {boolean}
 */
function isDeepInternalImport(specifier, layer, ctx) {
  const barrel = `${layer.importPrefix}${ctx}`;
  if (specifier === barrel || specifier === `${barrel}${INDEX_SUFFIX}`) {
    return false;
  }
  return specifier.startsWith(`${barrel}/`);
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
 * @property {string} from       importing file's owning context (or consumer name)
 * @property {string} to         imported (foreign) context
 * @property {string} specifier  the offending import specifier
 */

/**
 * Owner layers that enforce a public contract (consulted for every consumer).
 *
 * @returns {import("./feature-boundary.config.mjs").OwnerLayer[]}
 */
function publicContractLayers() {
  return OWNER_LAYERS.filter((layer) => layer.publicContract);
}

/**
 * Owner layers with NO public barrel (today: `features`). Any import of one of
 * these layers' contexts from a file that does not OWN that context (a foreign
 * feature, a module, or `app/`) is a cross-context edge — there is no barrel to
 * target, so EVERY such import counts. Consulted for every consumer, mirroring
 * `publicContractLayers()`.
 *
 * @returns {import("./feature-boundary.config.mjs").OwnerLayer[]}
 */
function barrelLessLayers() {
  return OWNER_LAYERS.filter((layer) => !layer.publicContract);
}

/**
 * Collect public-contract violations for one consuming file: any deep internal
 * import (`<prefix><ctx>/<internal>`) of a public-contract layer, except a file
 * reaching into its OWN module.
 *
 * @param {string} relPath importing file (ROOT-relative POSIX)
 * @param {string} from importing file's owning context (or consumer name)
 * @param {string|null} ownLayerName owner layer the file belongs to, or null
 * @param {string[]} specifiers
 * @returns {Violation[]}
 */
function publicContractViolations(relPath, from, ownLayerName, specifiers) {
  /** @type {Violation[]} */
  const violations = [];
  for (const layer of publicContractLayers()) {
    for (const specifier of specifiers) {
      if (!specifier.startsWith(layer.importPrefix)) {
        continue;
      }
      const ctx = contextOfImport(specifier, layer);
      if (!ctx) {
        continue;
      }
      // A module importing its own internals is allowed.
      const isOwnModule = ownLayerName === layer.name && ctx === from;
      if (isOwnModule) {
        continue;
      }
      if (isDeepInternalImport(specifier, layer, ctx)) {
        violations.push({ file: relPath, from, to: ctx, specifier });
      }
    }
  }
  return violations;
}

/**
 * Collect barrel-less cross-context violations for one consuming file: any
 * `<prefix><ctx>/...` import of a barrel-less owner layer (today: `features`),
 * EXCEPT a file reaching into its OWN context of that same layer.
 *
 * Applies to every consumer — a foreign feature, a `modules/<m>` file, and
 * `app/` — because barrel-less layers expose no public surface, so ANY deep
 * import of another context is cross-context.
 *
 * @param {string} relPath importing file (ROOT-relative POSIX)
 * @param {string} from importing file's owning context (or consumer name)
 * @param {string|null} ownLayerName owner layer the file belongs to, or null
 * @param {string[]} specifiers
 * @returns {Violation[]}
 */
function barrelLessViolations(relPath, from, ownLayerName, specifiers) {
  /** @type {Violation[]} */
  const violations = [];
  for (const layer of barrelLessLayers()) {
    for (const specifier of specifiers) {
      if (!specifier.startsWith(layer.importPrefix)) {
        continue;
      }
      const to = contextOfImport(specifier, layer);
      if (!to) {
        continue;
      }
      // A file may reach into its OWN context of this same layer.
      const isOwnContext = ownLayerName === layer.name && to === from;
      if (isOwnContext) {
        continue;
      }
      violations.push({ file: relPath, from, to, specifier });
    }
  }
  return violations;
}

/**
 * Scan every owner layer AND the app consumer, returning every cross-context
 * internal import (legacy cross-feature + module public-contract breaches).
 *
 * @returns {Violation[]} sorted deterministically by file then specifier
 */
export function scanCrossFeatureImports() {
  /** @type {Violation[]} */
  const violations = [];

  for (const layer of OWNER_LAYERS) {
    if (!existsSync(layer.dir)) {
      continue;
    }
    for (const absPath of walkSourceFiles(layer.dir)) {
      const relPath = toRelativePosix(absPath);
      const from = contextOfFile(relPath, layer);
      const specifiers = extractSpecifiers(readFileSync(absPath, "utf8"));

      // Module public-contract rule applies to other-module consumers too.
      violations.push(
        ...publicContractViolations(relPath, from, layer.name, specifiers),
      );

      // Barrel-less rule (features): ANY consumer importing a foreign feature
      // context is cross-context — including a `modules/<m>` file (it never
      // owns a feature context), closing the migration blind spot.
      violations.push(
        ...barrelLessViolations(relPath, from, layer.name, specifiers),
      );
    }
  }

  // The app consumer owns no context: every owner-layer rule applies to it.
  if (existsSync(APP_CONSUMER.dir)) {
    for (const absPath of walkSourceFiles(APP_CONSUMER.dir)) {
      const relPath = toRelativePosix(absPath);
      const specifiers = extractSpecifiers(readFileSync(absPath, "utf8"));
      violations.push(
        ...publicContractViolations(
          relPath,
          APP_CONSUMER.name,
          null,
          specifiers,
        ),
        ...barrelLessViolations(relPath, APP_CONSUMER.name, null, specifiers),
      );
    }
  }

  violations.sort(
    (a, b) =>
      a.file.localeCompare(b.file) || a.specifier.localeCompare(b.specifier),
  );
  return violations;
}

/**
 * Build the stable allowlist key for a violation: `<file>::<to-context>`.
 * Keyed by importing file + foreign context so adding a NEW foreign context to
 * an already-grandfathered file is still caught as a new violation.
 *
 * @param {Violation} violation
 * @returns {string}
 */
export function violationKey(violation) {
  return `${violation.file}::${violation.to}`;
}
