#!/usr/bin/env node
/**
 * Comment policy gate for frontend sources (.ts, .tsx, .js, .mjs, .cjs).
 *
 * Pedro's rule: source and test code carries no explanatory comments. Docs live
 * in JSDoc blocks. A comment is allowed only when it is:
 *   - a JSDoc block (`/** ... *\/`) that starts its own line;
 *   - a tool directive (eslint-*, @ts-expect-error, prettier-ignore, v8/c8/istanbul
 *     ignore, Stryker disable/restore, webpack magic comments, @vite-ignore,
 *     #__PURE__, triple-slash references, the integrity-ok: escape hatch read
 *     by scripts/ci/check-integrity.sh);
 *   - a Gherkin reference read by scripts/check_gherkin_refs.py
 *     (`// Scenario: <title>`), plus indented continuation lines
 *     (`//   rest`) directly below it when a long title wraps;
 *   - a licence header (@license, SPDX-License-Identifier, Copyright).
 * Ticket ids, decision ids and to-do markers (see TICKET_RE and MARKER_RE) are
 * rejected in every remaining comment, JSDoc included. A Gherkin reference is
 * exempt from the ticket-id check because it repeats the scenario title.
 *
 * Usage: node scripts/check-comments.mjs [FILE...]
 * Env:   COMMENTS_ROOT  scan this directory instead of the frontend tree (tests).
 * Exits 1 and lists `path:line: reason: comment` for every violation.
 */
import { readFileSync, readdirSync } from "node:fs";
import { join, relative } from "node:path";
import { parser } from "typescript-eslint";

const FRONTEND_ROOT = join(import.meta.dirname, "..");
const SCAN_DIRS = ["src", "tests", "scripts", ".storybook"];
const SKIP_DIRS = new Set(["node_modules", "braces-patched", ".next"]);
const SOURCE_RE = /\.(ts|tsx|js|mjs|cjs)$/;
const GENERATED = new Set(["next-env.d.ts"]);

const DIRECTIVE_RE =
  /^\s*(eslint-disable|eslint-enable|eslint\s|globals?\s|exported\s|@ts-expect-error|@ts-ignore|@ts-nocheck|@ts-check|prettier-ignore|[vc]8 ignore|istanbul ignore|Stryker (disable|restore)|webpack[A-Z]|@vite-ignore|[#@]__PURE__|@jsx|integrity-ok:|\/\s*<reference)/;
const SCENARIO_RE = /^\s*Scenario(?: Outline)?:\s*\S/;
const CONTINUATION_RE = /^\s{2,}\S/;
const LICENCE_RE = /@license|SPDX-License-Identifier:|Copyright\b/;
const TICKET_RE = /\b(?:AE-\d{2,5}|D-\d+)\b/;
const MARKER_RE = /\b(?:TODO|FIXME|XXX|HACK)\b/;

const REASON_COMMENT = "non-doc comment (move real information into JSDoc)";
const REASON_TICKET = "ticket or decision id";
const REASON_MARKER = "TODO/FIXME/XXX/HACK marker";

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (SKIP_DIRS.has(entry.name)) continue;
    const path = join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(path));
    else if (SOURCE_RE.test(entry.name) && !GENERATED.has(entry.name))
      out.push(path);
  }
  return out;
}

function defaultFiles() {
  const root = process.env.COMMENTS_ROOT;
  if (root) return walk(root);
  const files = readdirSync(FRONTEND_ROOT, { withFileTypes: true })
    .filter((e) => e.isFile() && SOURCE_RE.test(e.name))
    .filter((e) => !GENERATED.has(e.name))
    .map((e) => join(FRONTEND_ROOT, e.name));
  for (const dir of SCAN_DIRS) files.push(...walk(join(FRONTEND_ROOT, dir)));
  return files;
}

function standalone(code, comment) {
  const lineStart = code.lastIndexOf("\n", comment.range[0] - 1) + 1;
  return code.slice(lineStart, comment.range[0]).trim() === "";
}

function noiseReason(text) {
  if (TICKET_RE.test(text)) return REASON_TICKET;
  if (MARKER_RE.test(text)) return REASON_MARKER;
  return null;
}

function isJsDoc(code, comment) {
  return (
    comment.type === "Block" &&
    comment.value.startsWith("*") &&
    comment.value !== "*" &&
    standalone(code, comment)
  );
}

function isToolComment(comment) {
  return DIRECTIVE_RE.test(comment.value) || LICENCE_RE.test(comment.value);
}

/** Every comment of `code` the policy rejects, as `{ line, reason, text }`. */
export function checkSource(filePath, code) {
  const { ast } = parser.parseForESLint(code, {
    comment: true,
    jsx: filePath.endsWith("x") || filePath.endsWith(".js"),
    loc: true,
    range: true,
    filePath,
  });
  const violations = [];
  let scenarioLine = -2;
  for (const comment of ast.comments ?? []) {
    const line = comment.loc.start.line;
    const text = comment.type === "Line" ? `//${comment.value}` : `/*${comment.value}*/`;
    const alone = standalone(code, comment);
    if (alone && SCENARIO_RE.test(comment.value)) {
      scenarioLine = comment.loc.end.line;
      continue;
    }
    const continues =
      line === scenarioLine + 1 && CONTINUATION_RE.test(comment.value);
    if (alone && comment.type === "Line" && continues) {
      scenarioLine = line;
      continue;
    }
    if (isJsDoc(code, comment) || isToolComment(comment)) {
      const reason = noiseReason(comment.value);
      if (reason) violations.push({ line, reason, text });
      continue;
    }
    violations.push({ line, reason: REASON_COMMENT, text });
  }
  return violations;
}

function main(args) {
  const files = args.length > 0 ? args : defaultFiles();
  let total = 0;
  for (const file of files) {
    const code = readFileSync(file, "utf8");
    for (const v of checkSource(file, code)) {
      const snippet = v.text.trim().split("\n")[0];
      process.stdout.write(
        `${relative(FRONTEND_ROOT, file)}:${v.line}: ${v.reason}: ${snippet}\n`,
      );
      total += 1;
    }
  }
  if (total > 0) {
    process.stderr.write(
      `\n${total} comment policy violation(s). Only JSDoc, tool directives and ` +
        `Gherkin "Scenario:" references are allowed.\n`,
    );
    process.exit(1);
  }
  process.stdout.write(
    `comment policy OK (${files.length} source files scanned).\n`,
  );
}

if (process.argv[1] === import.meta.filename) main(process.argv.slice(2));
