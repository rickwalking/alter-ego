/**
 * Gherkin: tests/features/frontend-legacy-removal.feature
 * Scenario: Dashboard chat source must not import ChatInterface
 * Scenario: Legacy route group must not exist after Phase 1
 */
import { execSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const FRONTEND_ROOT = join(import.meta.dirname, "..", "..");
const CHECK_SCRIPT = join(FRONTEND_ROOT, "scripts", "check-legacy-usage.mjs");

function runGuard(args: string): { status: number; output: string } {
  try {
    const output = execSync(`node "${CHECK_SCRIPT}" ${args}`, {
      cwd: FRONTEND_ROOT,
      encoding: "utf8",
      stdio: ["pipe", "pipe", "pipe"],
    });
    return { status: 0, output };
  } catch (err) {
    const error = err as { status?: number; stdout?: string; stderr?: string };
    return {
      status: error.status ?? 1,
      output: `${error.stdout ?? ""}${error.stderr ?? ""}`,
    };
  }
}

describe("Frontend legacy removal guard", () => {
  describe("Given the legacy usage guard runs on the repository", () => {
    it("Then check:legacy passes (no forbidden dashboard imports or routes)", () => {
      const { status, output } = runGuard("");
      expect(status, output).toBe(0);
      expect(output).toContain("Legacy usage guard passed");
    });

    it("Then no file under src/app/dashboard imports ChatInterface", () => {
      expect(existsSync(CHECK_SCRIPT)).toBe(true);
      const { status } = runGuard("");
      expect(status).toBe(0);
    });
  });

  describe("Given the legacy inventory check runs on the repository", () => {
    it("Then inventory mode passes after Phase 1 deletions", () => {
      const { status, output } = runGuard("--inventory");
      expect(status, output).toBe(0);
      expect(output).toContain("inventory check passed");
    });
  });
});
