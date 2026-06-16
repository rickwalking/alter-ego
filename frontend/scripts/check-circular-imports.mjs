#!/usr/bin/env node
/**
 * Dependency-free circular-import detector for `src/**` (AE-0136).
 *
 * Barrel (`index.ts`) consolidation under `modules/` is a classic source of
 * import cycles that tsc/eslint/Vitest do NOT catch. Rather than add an npm
 * dependency (e.g. `madge`), this builds the intra-`src` import graph by
 * resolving `@/...` (tsconfig alias `@/* -> ./src/*`) and relative (`./`,
 * `../`) specifiers to files, then reports any strongly-connected import cycle.
 *
 * Usage:
 *   node scripts/check-circular-imports.mjs   # exit 1 if any cycle is found
 *
 * npm script: `lint:circular`. Must report 0 cycles at the Phase 7 baseline and
 * stay at 0 as features migrate behind module barrels.
 *
 * Scope: tests / stories are excluded (not shipped graph). Type-only imports
 * are included — a `import type` cycle is still a maintenance hazard and Next's
 * RSC graph treats the module graph as a whole.
 */

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(fileURLToPath(new URL(".", import.meta.url)), "..");
const SRC_DIR = join(ROOT, "src");
const ALIAS_PREFIX = "@/";
const SOURCE_EXTENSIONS = [".ts", ".tsx"];
const EXCLUDE_PATTERNS = [".test.", ".stories.", ".spec.", ".d.ts"];

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
 * @returns {string[]} absolute source file paths under `dir`
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
 * @param {string} absPath
 * @returns {string} ROOT-relative POSIX path
 */
function toRelativePosix(absPath) {
  return relative(ROOT, absPath).split(sep).join("/");
}

/**
 * Resolve a module-or-index candidate path to a concrete source file.
 * Tries `<base>.ts`, `<base>.tsx`, `<base>/index.ts`, `<base>/index.tsx`,
 * and (if it already ends in a tracked extension) the literal path.
 *
 * @param {string} base absolute path WITHOUT an extension (or with one)
 * @returns {string|null} absolute resolved file path, or null
 */
function resolveToFile(base) {
  if (SOURCE_EXTENSIONS.some((ext) => base.endsWith(ext)) && existsSync(base)) {
    return base;
  }
  for (const ext of SOURCE_EXTENSIONS) {
    const candidate = `${base}${ext}`;
    if (existsSync(candidate)) {
      return candidate;
    }
  }
  if (existsSync(base) && statSync(base).isDirectory()) {
    for (const ext of SOURCE_EXTENSIONS) {
      const candidate = join(base, `index${ext}`);
      if (existsSync(candidate)) {
        return candidate;
      }
    }
  }
  return null;
}

/**
 * Resolve an import specifier from `fromFile` to an absolute source file inside
 * `src`, or null if it is external / unresolvable / outside src.
 *
 * @param {string} specifier
 * @param {string} fromFile absolute path of the importing file
 * @returns {string|null}
 */
function resolveSpecifier(specifier, fromFile) {
  let base;
  if (specifier.startsWith(ALIAS_PREFIX)) {
    base = join(SRC_DIR, specifier.slice(ALIAS_PREFIX.length));
  } else if (specifier.startsWith("./") || specifier.startsWith("../")) {
    base = resolve(dirname(fromFile), specifier);
  } else {
    return null; // bare/external import
  }
  const resolved = resolveToFile(base);
  if (!resolved) {
    return null;
  }
  // Only track edges that stay within src/.
  return resolved.startsWith(SRC_DIR + sep) ? resolved : null;
}

/**
 * @param {string} content
 * @returns {string[]}
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
 * Build the intra-src import graph: node -> set of imported nodes (abs paths).
 *
 * @returns {Map<string, Set<string>>}
 */
function buildGraph() {
  /** @type {Map<string, Set<string>>} */
  const graph = new Map();
  const files = walkSourceFiles(SRC_DIR);
  for (const file of files) {
    graph.set(file, new Set());
  }
  for (const file of files) {
    const content = readFileSync(file, "utf8");
    const edges = graph.get(file);
    for (const specifier of extractSpecifiers(content)) {
      const target = resolveSpecifier(specifier, file);
      if (target && target !== file && graph.has(target)) {
        edges.add(target);
      }
    }
  }
  return graph;
}

/**
 * Tarjan's strongly-connected-components: any SCC with >1 node, or a node with a
 * self-loop, is a cycle.
 *
 * @param {Map<string, Set<string>>} graph
 * @returns {string[][]} list of cycles (each a list of ROOT-relative paths)
 */
function findCycles(graph) {
  let index = 0;
  /** @type {Map<string, number>} */
  const idx = new Map();
  /** @type {Map<string, number>} */
  const low = new Map();
  /** @type {Set<string>} */
  const onStack = new Set();
  /** @type {string[]} */
  const stack = [];
  /** @type {string[][]} */
  const cycles = [];

  /** @param {string} v */
  function strongConnect(v) {
    idx.set(v, index);
    low.set(v, index);
    index += 1;
    stack.push(v);
    onStack.add(v);

    for (const w of graph.get(v) ?? []) {
      if (!idx.has(w)) {
        strongConnect(w);
        low.set(v, Math.min(low.get(v), low.get(w)));
      } else if (onStack.has(w)) {
        low.set(v, Math.min(low.get(v), idx.get(w)));
      }
    }

    if (low.get(v) === idx.get(v)) {
      /** @type {string[]} */
      const component = [];
      let w;
      do {
        w = stack.pop();
        onStack.delete(w);
        component.push(w);
      } while (w !== v);

      const hasSelfLoop = (graph.get(v) ?? new Set()).has(v);
      if (component.length > 1 || hasSelfLoop) {
        cycles.push(component.map(toRelativePosix).sort());
      }
    }
  }

  // Iterate deterministically.
  for (const v of [...graph.keys()].sort()) {
    if (!idx.has(v)) {
      strongConnect(v);
    }
  }
  return cycles;
}

function main() {
  const graph = buildGraph();
  const cycles = findCycles(graph);

  if (cycles.length > 0) {
    process.stderr.write(
      `\nCircular-import check FAILED: ${cycles.length} import cycle(s) found in src/:\n`,
    );
    for (const cycle of cycles) {
      process.stderr.write(`  - cycle (${cycle.length} files):\n`);
      for (const file of cycle) {
        process.stderr.write(`      ${file}\n`);
      }
    }
    process.stderr.write(
      "\nBreak the cycle (often a barrel `index.ts` re-export loop) before merging.\n",
    );
    process.exit(1);
  }

  process.stdout.write(
    `Circular-import check OK: 0 cycles across ${graph.size} src/ module(s).\n`,
  );
}

main();
