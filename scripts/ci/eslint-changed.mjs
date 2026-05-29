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

const result = spawnSync(
  "npx",
  ["eslint", "--max-warnings=0", ...files],
  { cwd: frontendDir, stdio: "inherit", shell: false },
);

process.exit(result.status ?? 1);
