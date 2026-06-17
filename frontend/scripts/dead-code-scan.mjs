#!/usr/bin/env node
/**
 * Dead-code (unused export/type) scanning + classification for the AE-0152
 * frontend dead-export gate. Wraps `knip` and exposes pure helpers so the
 * ratchet logic is unit-testable (see dead-code.test.ts).
 *
 * Identity model (skeptical-review BLOCKER): a finding is keyed by
 * `type|file|symbol` — NOT by a total count, and deliberately WITHOUT line/col
 * so unrelated edits don't churn the baseline. A replace-same-count change
 * (remove one grandfathered orphan, add a new one) therefore fails, because the
 * new identity is not in the allowlist.
 */

import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const FRONTEND_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

/** knip issue kinds that represent an unused exported symbol. */
export const EXPORT_ISSUE_KINDS = ["exports", "types", "nsExports", "nsTypes"];

const KIND_LABEL = {
  exports: "export",
  types: "type",
  nsExports: "ns-export",
  nsTypes: "ns-type",
};

/** Stable identity for a finding: `type|file|symbol` (no line/col). */
export function identityKey({ type, file, name }) {
  return `${type}|${file}|${name}`;
}

/**
 * Parse knip's JSON report into a flat list of unused-export findings.
 * @param {object} report - parsed `knip --reporter json` output
 * @returns {Array<{key:string,type:string,file:string,name:string,line:number}>}
 */
export function parseKnipReport(report) {
  const findings = [];
  for (const issue of report.issues ?? []) {
    const file = issue.file;
    for (const kind of EXPORT_ISSUE_KINDS) {
      for (const entry of issue[kind] ?? []) {
        const type = KIND_LABEL[kind];
        findings.push({
          key: identityKey({ type, file, name: entry.name }),
          type,
          file,
          name: entry.name,
          line: entry.line ?? 0,
        });
      }
    }
  }
  findings.sort((a, b) => a.key.localeCompare(b.key));
  return findings;
}

/**
 * Classify findings against the grandfathered allowlist.
 *
 * - `blocking`: net-new findings the gate must FAIL on. By default that is
 *   net-new findings whose file changed in this PR (day-one changed-file
 *   blocking). When `fullTreeBlocking` is true (the future flip), ALL net-new
 *   findings block.
 * - `advisory`: net-new findings reported but non-blocking (full-tree sweep of
 *   pre-existing unchanged files until the flip).
 * - `resolved`: grandfathered identities no longer present (baseline may shrink).
 *
 * @param {{findings:Array, allowed:Set<string>, changedFiles:Set<string>, fullTreeBlocking?:boolean}} args
 */
export function classifyDeadCode({
  findings,
  allowed,
  changedFiles,
  fullTreeBlocking = false,
}) {
  const netNew = findings.filter((f) => !allowed.has(f.key));
  const blocking = netNew.filter(
    (f) => fullTreeBlocking || changedFiles.has(f.file),
  );
  const blockingKeys = new Set(blocking.map((f) => f.key));
  const advisory = netNew.filter((f) => !blockingKeys.has(f.key));
  const presentKeys = new Set(findings.map((f) => f.key));
  const resolved = [...allowed].filter((k) => !presentKeys.has(k));
  return { netNew, blocking, advisory, resolved };
}

/** Run knip and return parsed findings. Throws only on a real knip failure. */
export function scanDeadCodeExports() {
  let stdout;
  try {
    stdout = execFileSync(
      "npx",
      [
        "knip",
        "--include",
        EXPORT_ISSUE_KINDS.join(","),
        "--reporter",
        "json",
        "--no-exit-code",
      ],
      { cwd: FRONTEND_ROOT, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 },
    );
  } catch (err) {
    // knip exits non-zero when it finds issues; with --no-exit-code it should
    // not, but be defensive and still parse stdout if present.
    stdout = err.stdout?.toString() ?? "";
    if (!stdout) throw err;
  }
  return parseKnipReport(JSON.parse(stdout));
}
