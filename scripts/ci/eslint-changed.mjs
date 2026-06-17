#!/usr/bin/env node
/**
 * Run ESLint on files changed vs origin/main (frontend diff-scoped gate).
 */
import { execFileSync, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const frontendDir = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../frontend",
);
const scriptPath = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "changed-frontend-files.sh",
);

const files = execFileSync("bash", [scriptPath], {
  cwd: path.resolve(frontendDir, ".."),
  encoding: "utf8",
})
  .trim()
  .split("\n")
  .filter(Boolean);

if (files.length === 0) {
  console.log("No changed frontend source files — skipping diff-scoped ESLint.");
  process.exit(0);
}

// Diff-scoped lint. `error`-level rules GATE (non-zero exit fails CI). `warn`
// rules are SURFACED here (no `--quiet`, unlike the full-repo `lint` gate) as a
// paydown nudge on the exact files a PR touches, but are NOT gating — a strict
// `--max-warnings=0` would force unrelated refactors of pre-existing warnings in
// any file you so much as add a line to. See the severity policy in
// frontend/eslint.config.mjs (AE-0166).
const result = spawnSync("npx", ["eslint", ...files], {
  cwd: frontendDir,
  stdio: "inherit",
  shell: false,
});

process.exit(result.status ?? 1);
