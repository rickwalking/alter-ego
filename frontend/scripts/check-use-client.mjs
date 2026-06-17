#!/usr/bin/env node
/**
 * AE-0166 — a `.tsx` component that calls client-only React hooks MUST declare
 * `"use client"`. Catches the missing-directive class that previously only
 * `next build` flagged (AE-0155) — now caught statically by `npm run lint`.
 *
 * Scope: component files (`.tsx`) under src/, excluding tests/stories. Custom
 * hook modules (`.ts`) are intentionally NOT checked — the client boundary is
 * the component, and a hook module inherits its consumer's directive.
 *
 * Env: USE_CLIENT_ROOT  override the scan root (default "src"; used by tests).
 */
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const ROOT = process.env.USE_CLIENT_ROOT || "src";

// Hooks that REQUIRE a Client Component (state/effect/refs/context/etc.).
const HOOK_RE =
  /\b(useState|useEffect|useLayoutEffect|useReducer|useRef|useContext|useImperativeHandle|useTransition|useDeferredValue|useSyncExternalStore)\s*\(/;
const DIRECTIVE_RE = /^\s*["']use client["']/;

// Strip block + line comments so a hook name mentioned only in a comment is not
// a false positive, and a `"use client"` directive preceded by a leading
// license/JSDoc block (legal per Next.js) is still recognized. String-literal
// `//` (e.g. in URLs) is left alone via the leading-boundary group.
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:'"`])\/\/.*$/gm, "$1");
}

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name.startsWith(".")) continue;
    const p = join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walk(p));
    } else if (p.endsWith(".tsx") && !/\.(test|spec|stories)\.tsx$/.test(p)) {
      out.push(p);
    }
  }
  return out;
}

const files = walk(ROOT);
const violations = [];
for (const file of files) {
  const code = stripComments(readFileSync(file, "utf8"));
  if (!HOOK_RE.test(code)) continue;
  // The directive must be the first statement, but comments/blank lines may
  // precede it — stripComments() turned those into whitespace, so the directive
  // is now the first non-blank content if present.
  if (!DIRECTIVE_RE.test(code.replace(/^\s+/, ""))) violations.push(file);
}

if (violations.length > 0) {
  process.stderr.write(
    `\nMissing "use client" — ${violations.length} component file(s) call ` +
      `client-only React hooks without the directive (AE-0166):\n`,
  );
  for (const v of violations) process.stderr.write(`  ✗ ${v}\n`);
  process.stderr.write(
    `\nAdd \`"use client";\` as the first line, or move the hook usage into a ` +
      `Client Component. (next build fails on this too — AE-0155.)\n`,
  );
  process.exit(1);
}

process.stdout.write(
  `use-client check OK (${files.length} component files scanned).\n`,
);
