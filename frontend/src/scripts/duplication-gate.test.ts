/**
 * Gherkin: tests/features/duplication-gate.feature
 * Scenario: New source duplication above threshold is rejected
 * Scenario: Distinct source files pass the gate
 * Scenario: Test boilerplate does not trip the blocking gate
 * Scenario: The committed source duplication stays at or below the threshold
 *
 * Proves the AE-0149 jscpd gate actually enforces: a seeded duplicate block
 * makes jscpd exit non-zero, distinct files pass, and the ignore globs keep
 * test boilerplate out of the blocking gate.
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

const FRONTEND_ROOT = join(import.meta.dirname, "..", "..");
const JSCPD_BIN = join(FRONTEND_ROOT, "node_modules", ".bin", "jscpd");
const JSCPD_CONFIG = join(FRONTEND_ROOT, ".jscpd.json");

// A ≥5-line / ≥50-token block — large enough to exceed minLines:5 / minTokens:50.
const DUPLICATED_BLOCK = `
export function accumulateStreamTokens(previous: string, token: string): string {
  const trimmed = token.replace(/\\u0000/g, "");
  const next = previous + trimmed;
  const normalized = next.replace(/\\r\\n/g, "\\n");
  const collapsed = normalized.replace(/\\n{3,}/g, "\\n\\n");
  const guarded = collapsed.length > 100000 ? collapsed.slice(0, 100000) : collapsed;
  return guarded.trimEnd();
}
`;

function runJscpdOn(
  targetDir: string,
  extraArgs: readonly string[] = [],
): { status: number; output: string } {
  try {
    const output = execFileSync(
      JSCPD_BIN,
      [
        targetDir,
        "--format",
        "typescript,tsx",
        "--min-tokens",
        "50",
        "--min-lines",
        "5",
        "--threshold",
        "0",
        "--reporters",
        "console",
        "--silent",
        ...extraArgs,
      ],
      { cwd: FRONTEND_ROOT, encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] },
    );
    return { status: 0, output };
  } catch (err) {
    const error = err as { status?: number; stdout?: string; stderr?: string };
    return {
      status: error.status ?? 1,
      output: `${error.stdout ?? ""}${error.stderr ?? ""}`,
    };
  }
}

describe("Frontend duplication gate (AE-0149)", () => {
  let workDir: string;

  beforeEach(() => {
    workDir = mkdtempSync(join(tmpdir(), "jscpd-gate-"));
  });

  afterEach(() => {
    rmSync(workDir, { recursive: true, force: true });
  });

  describe("Given a duplicated block exists across two source files", () => {
    it("Then jscpd exits non-zero (gate enforces)", () => {
      const fileBody = `${DUPLICATED_BLOCK}\nexport const TAG = "x";\n`;
      writeFileSync(join(workDir, "alpha.ts"), fileBody);
      writeFileSync(join(workDir, "beta.ts"), fileBody);

      const { status, output } = runJscpdOn(workDir);

      expect(status, output).not.toBe(0);
      expect(output.toLowerCase()).toContain("clone");
    });
  });

  describe("Given two source files share no duplicated block", () => {
    it("Then jscpd exits zero (gate passes)", () => {
      writeFileSync(
        join(workDir, "alpha.ts"),
        `export const ALPHA = 1;\nexport const A2 = 2;\nexport const A3 = 3;\n`,
      );
      writeFileSync(
        join(workDir, "beta.ts"),
        `export function beta(): number {\n  return 42;\n}\n`,
      );

      const { status, output } = runJscpdOn(workDir);

      expect(status, output).toBe(0);
    });
  });

  describe("Given a duplicated block exists only in *.test.ts files", () => {
    it("Then the blocking gate ignores it (test/spec/story globs excluded)", () => {
      const fileBody = `${DUPLICATED_BLOCK}\nexport const TAG = "x";\n`;
      writeFileSync(join(workDir, "alpha.test.ts"), fileBody);
      writeFileSync(join(workDir, "beta.test.ts"), fileBody);

      const { status, output } = runJscpdOn(workDir, [
        "--ignore",
        "**/*.test.*,**/*.spec.*,**/*.stories.*",
      ]);

      expect(status, output).toBe(0);
    });
  });

  describe("Given the committed frontend/.jscpd.json", () => {
    const config = JSON.parse(readFileSync(JSCPD_CONFIG, "utf8")) as {
      threshold: number;
      ignore: string[];
      format: string[];
    };

    it("Then test/spec/story globs are excluded from the blocking gate", () => {
      expect(config.ignore).toEqual(
        expect.arrayContaining([
          "**/*.test.*",
          "**/*.spec.*",
          "**/*.stories.*",
        ]),
      );
    });

    it("Then the measured source duplication does not exceed the threshold", () => {
      const { status, output } = (() => {
        try {
          const out = execFileSync(JSCPD_BIN, ["src"], {
            cwd: FRONTEND_ROOT,
            encoding: "utf8",
            stdio: ["pipe", "pipe", "pipe"],
          });
          return { status: 0, output: out };
        } catch (err) {
          const e = err as { status?: number; stdout?: string };
          return { status: e.status ?? 1, output: e.stdout ?? "" };
        }
      })();

      expect(status, output).toBe(0);
    });
  });
});
