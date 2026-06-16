/**
 * Inline component/hook type-declaration scanner shared by the checker and the
 * baseline generator, so both compute violations identically (AE-0144).
 *
 * Detects NON-TRIVIAL object-shape types declared inline in a component
 * (`*.tsx`) or hook (`use-*.ts`) file under `src/modules/**`:
 *
 *   - `interface Foo { ... }`   (any interface block, exported or not)
 *   - `type Foo = { ... }`      (object-literal type alias)
 *
 * Trivial aliases (`type X = "a" | "b";`, `type X = z.infer<...>;`) are NOT
 * object shapes and are ignored. See `component-type-location.config.mjs` for
 * the full convention and the rationale for the governed-file set.
 */

import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join, relative, sep } from "node:path";

import {
  isGovernedFile,
  MODULES_DIR,
  ROOT,
} from "./component-type-location.config.mjs";

/**
 * Matches an inline `interface Name` declaration at the start of a line
 * (optionally `export`ed). Captures the declared name.
 */
const INTERFACE_RE = /^\s*(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)\b/;

/**
 * Matches an inline object-literal `type Name<...> = {` declaration at the
 * start of a line (optionally `export`ed). The trailing `= {` is what makes it
 * an object shape — union/derived aliases (`= "a" | "b"`, `= z.infer<...>`) do
 * not match and are intentionally left out of scope. Captures the name.
 */
const TYPE_OBJECT_RE =
  /^\s*(?:export\s+)?type\s+([A-Za-z_$][\w$]*)(?:<[^>]*>)?\s*=\s*\{/;

/**
 * @param {string} dir
 * @returns {string[]} absolute file paths under `dir` (recursive)
 */
function walkFiles(dir) {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walkFiles(full));
      continue;
    }
    out.push(full);
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
 * @typedef {object} Violation
 * @property {string} file ROOT-relative POSIX path of the declaring file
 * @property {string} kind `interface` or `type`
 * @property {string} name the declared type name (e.g. `RichTextEditorProps`)
 */

/**
 * Extract inline object-shape declarations from one file's contents.
 *
 * @param {string} relPath ROOT-relative POSIX path (for the violation record)
 * @param {string} content
 * @returns {Violation[]}
 */
function declarationsIn(relPath, content) {
  /** @type {Violation[]} */
  const violations = [];
  for (const line of content.split("\n")) {
    const interfaceMatch = INTERFACE_RE.exec(line);
    if (interfaceMatch) {
      violations.push({
        file: relPath,
        kind: "interface",
        name: interfaceMatch[1],
      });
      continue;
    }
    const typeMatch = TYPE_OBJECT_RE.exec(line);
    if (typeMatch) {
      violations.push({ file: relPath, kind: "type", name: typeMatch[1] });
    }
  }
  return violations;
}

/**
 * Scan every governed component/hook file, returning each inline object-shape
 * declaration as a violation.
 *
 * @returns {Violation[]} sorted deterministically by file then name
 */
export function scanInlineComponentTypes() {
  /** @type {Violation[]} */
  const violations = [];

  if (existsSync(MODULES_DIR)) {
    for (const absPath of walkFiles(MODULES_DIR)) {
      const relPath = toRelativePosix(absPath);
      if (!isGovernedFile(relPath)) {
        continue;
      }
      violations.push(
        ...declarationsIn(relPath, readFileSync(absPath, "utf8")),
      );
    }
  }

  violations.sort(
    (a, b) => a.file.localeCompare(b.file) || a.name.localeCompare(b.name),
  );
  return violations;
}

/**
 * Build the stable allowlist key for a violation: `<file>::<kind>::<name>`.
 * Keyed by file + declared name so adding a NEW inline type to an
 * already-grandfathered file is still caught as a new violation.
 *
 * @param {Violation} violation
 * @returns {string}
 */
export function violationKey(violation) {
  return `${violation.file}::${violation.kind}::${violation.name}`;
}
