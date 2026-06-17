/**
 * AE-0170: external QA/kaizen runs are isolated in a throwaway git worktree, and
 * a rogue HEAD-detach / branch-move of the primary repo is detected + restored.
 * Delegates to the self-contained bash check (uses temp repos; never touches the
 * working repo).
 */
import { execFileSync } from "node:child_process";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = join(import.meta.dirname, "..", "..", "..");
const CHECK = join(
  REPO_ROOT,
  "scripts",
  "lib",
  "external_agent_guard_check.sh",
);

describe("external_agent worktree isolation + HEAD-detach guard (AE-0170)", () => {
  it("isolates runs, detects+restores a rogue detach, and cleans the worktree", () => {
    let output = "";
    let status = 0;
    try {
      output = execFileSync("bash", [CHECK], {
        cwd: REPO_ROOT,
        encoding: "utf8",
        stdio: ["pipe", "pipe", "pipe"],
      });
    } catch (err) {
      const e = err as { status?: number; stdout?: string; stderr?: string };
      status = e.status ?? 1;
      output = `${e.stdout ?? ""}${e.stderr ?? ""}`;
    }
    expect(status, output).toBe(0);
    expect(output).toContain("guard-check OK");
  });
});
