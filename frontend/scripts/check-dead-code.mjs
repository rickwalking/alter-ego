#!/usr/bin/env node
/**
 * Frontend dead-export gate (AE-0152). Runs knip, compares unused exports/types
 * against the grandfathered baseline, and enforces the ratchet:
 *
 *   - NET-NEW finding in a PR-changed file -> BLOCK (day-one changed-file
 *     blocking). This is what fails CI.
 *   - NET-NEW finding in an unchanged file -> advisory (reported, non-blocking)
 *     — the full-tree sweep of pre-existing debt until the flip.
 *   - Grandfathered finding (in the baseline) -> ignored.
 *   - Resolved grandfathered identities -> reported (baseline may ratchet DOWN).
 *
 * Flip to full-tree blocking by setting DEAD_CODE_FULL_TREE_BLOCKING=1 once the
 * grandfathered count reaches 0 (see frontend/AGENTS.md operating-model note).
 *
 * Run as: npm run lint:dead-code   (gates.sh frontend:dead-code)
 * Diff base: GATES_BASE_REF (default origin/main).
 */
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { BASELINE_PATH, REGEN_HINT } from "./dead-code.config.mjs";
import { classifyDeadCode, scanDeadCodeExports } from "./dead-code-scan.mjs";

const FRONTEND_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const REPO_ROOT = resolve(FRONTEND_ROOT, "..");
const BASE_REF = process.env.GATES_BASE_REF || "origin/main";
const FULL_TREE_BLOCKING = process.env.DEAD_CODE_FULL_TREE_BLOCKING === "1";

function loadBaseline() {
  if (!existsSync(BASELINE_PATH)) {
    process.stderr.write(
      `Dead-code baseline missing at ${BASELINE_PATH}. ${REGEN_HINT}\n`,
    );
    process.exit(1);
  }
  const parsed = JSON.parse(readFileSync(BASELINE_PATH, "utf8"));
  return new Set(parsed.allowlist ?? []);
}

function gitDiffNames(range) {
  const out = execFileSync("git", ["diff", "--name-only", ...range], {
    cwd: REPO_ROOT,
    encoding: "utf8",
  });
  return new Set(
    out
      .split("\n")
      .filter((p) => p.startsWith("frontend/"))
      .map((p) => p.slice("frontend/".length)),
  );
}

/**
 * Files changed vs BASE_REF, normalized to frontend-relative `src/...` paths.
 * Prefers the merge-base (`BASE...HEAD`); falls back to a direct two-ref diff
 * (`BASE HEAD`) when there is no merge base (e.g. a stacked branch whose base
 * ref has diverged), so the gate still works off a stacked PR.
 *
 * This is the canonical REFERENCE implementation of the 3-tier fallback. The
 * shared bash port `scripts/lib/diff_base.sh` (AE-0177) mirrors this logic for
 * the bash gates (check-integrity, changed-{frontend,backend}-files, ruff-strict);
 * keep the two in parity. Kept in JS here to avoid a node->bash shell-out on the
 * hot dead-code path.
 */
function changedFrontendFiles() {
  try {
    return gitDiffNames([`${BASE_REF}...HEAD`]);
  } catch {
    try {
      return gitDiffNames([BASE_REF, "HEAD"]);
    } catch {
      process.stderr.write(
        `dead-code: could not diff vs ${BASE_REF} (advisory-only this run).\n`,
      );
      return null;
    }
  }
}

function main() {
  const allowed = loadBaseline();
  const changed = changedFrontendFiles();
  const findings = scanDeadCodeExports();

  // If we cannot determine changed files, never block on changed-file logic.
  const { blocking, advisory, resolved } = classifyDeadCode({
    findings,
    allowed,
    changedFiles: changed ?? new Set(),
    fullTreeBlocking: FULL_TREE_BLOCKING && changed !== null,
  });

  if (advisory.length) {
    process.stdout.write(
      `\nADVISORY: ${advisory.length} pre-existing/unchanged-file unused export(s) (non-blocking):\n`,
    );
    for (const f of advisory.slice(0, 20)) {
      process.stdout.write(`  ~ ${f.file}:${f.line} ${f.type} ${f.name}\n`);
    }
    if (advisory.length > 20) {
      process.stdout.write(`  ... and ${advisory.length - 20} more\n`);
    }
  }

  if (resolved.length) {
    process.stdout.write(
      `\nINFO: ${resolved.length} grandfathered unused export(s) resolved — ` +
        `run \`npm run dead-code:baseline\` to ratchet the baseline DOWN.\n`,
    );
  }

  if (blocking.length) {
    process.stderr.write(
      `\nFAIL: ${blocking.length} NEW unused export(s) in changed files ` +
        `(dead code — remove the export or use it):\n`,
    );
    for (const f of blocking) {
      process.stderr.write(`  ✗ ${f.file}:${f.line} ${f.type} ${f.name}\n`);
    }
    process.stderr.write(
      `\nThe export is declared but nothing imports it. Delete it, or wire it ` +
        `up. Do not add it to the baseline (the baseline is down-only). ${REGEN_HINT}\n`,
    );
    process.exit(1);
  }

  process.stdout.write(
    `\nDead-code gate OK: 0 new unused exports in changed files ` +
      `(${allowed.size} grandfathered, ${advisory.length} advisory).\n`,
  );
}

main();
