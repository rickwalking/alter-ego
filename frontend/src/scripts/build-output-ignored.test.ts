/**
 * AE-0171: the build-output gitignore pre-flight. Documented build/coverage
 * outputs must be gitignored; the check FAILS on a seeded non-ignored output.
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

const REPO_ROOT = join(import.meta.dirname, "..", "..", "..");
const SCRIPT = join(
  REPO_ROOT,
  "scripts",
  "ci",
  "check-build-output-ignored.sh",
);

function runCheck(env: Record<string, string> = {}): {
  status: number;
  output: string;
} {
  try {
    const output = execFileSync("bash", [SCRIPT], {
      cwd: REPO_ROOT,
      encoding: "utf8",
      env: { ...process.env, ...env },
      stdio: ["pipe", "pipe", "pipe"],
    });
    return { status: 0, output };
  } catch (err) {
    const e = err as { status?: number; stdout?: string; stderr?: string };
    return {
      status: e.status ?? 1,
      output: `${e.stdout ?? ""}${e.stderr ?? ""}`,
    };
  }
}

describe("build-output gitignore pre-flight (AE-0171)", () => {
  let workDir: string;

  beforeEach(() => {
    workDir = mkdtempSync(join(tmpdir(), "build-outputs-"));
  });
  afterEach(() => {
    rmSync(workDir, { recursive: true, force: true });
  });

  it("passes on the real repo (all documented outputs are gitignored)", () => {
    const { status, output } = runCheck();
    expect(status, output).toBe(0);
    expect(output).toContain("pre-flight OK");
  });

  it("FAILS on a seeded build output that is not gitignored", () => {
    const map = join(workDir, "build-outputs.txt");
    writeFileSync(
      map,
      "frontend/.next\nfrontend/__NOT_IGNORED_PROBE__   # seeded\n",
    );
    const { status, output } = runCheck({ BUILD_OUTPUTS_FILE: map });
    expect(status, output).not.toBe(0);
    expect(output).toContain("__NOT_IGNORED_PROBE__");
  });

  it("passes when the seeded map lists only ignored outputs", () => {
    const map = join(workDir, "build-outputs.txt");
    writeFileSync(map, "frontend/.next\nfrontend/storybook-static\n");
    const { status, output } = runCheck({ BUILD_OUTPUTS_FILE: map });
    expect(status, output).toBe(0);
  });
});
