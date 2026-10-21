/**
 * AE-0446 rule-fires regression test (AE-0180): the two type-aware rules that
 * were advisory `warn`s since AE-0166 are now ESLint ERRORS in production `src`:
 * `@typescript-eslint/no-unnecessary-condition` and
 * `@typescript-eslint/prefer-nullish-coalescing`. Their backlog (69 + 50 at
 * AE-0166, 65 + 5 at the AE-0446 baseline) was paid down to 0 before the
 * promotion; this test proves a seeded violation of each still fails the lint.
 *
 * A probe module is written under a real `src/modules/**` path so it is
 * matched by the flat config + tsconfig project, then linted via the ESLint CLI.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

const FRONTEND_ROOT = join(import.meta.dirname, "..", "..");
const ESLINT_BIN = join(
  FRONTEND_ROOT,
  "node_modules",
  "eslint",
  "bin",
  "eslint.js",
);
const PROBE_DIR_NAME = "__eslint_strict_type_probe__";
const PROBE_DIR = join(FRONTEND_ROOT, "src", "modules", PROBE_DIR_NAME);
const PROBE = join(PROBE_DIR, "probe.ts");
const NO_UNNECESSARY_CONDITION = "@typescript-eslint/no-unnecessary-condition";
const PREFER_NULLISH = "@typescript-eslint/prefer-nullish-coalescing";
const SEVERITY_ERROR = 2;
const ESLINT_SUBPROCESS_TIMEOUT_MS = 60_000;

interface EslintMessage {
  ruleId: string | null;
  severity: number;
}
interface EslintResult {
  messages: EslintMessage[];
}

function lintProbe(): { exitCode: number; messages: EslintMessage[] } {
  try {
    const out = execFileSync(
      process.execPath,
      [
        ESLINT_BIN,
        "--format",
        "json",
        `src/modules/${PROBE_DIR_NAME}/probe.ts`,
      ],
      { cwd: FRONTEND_ROOT, encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] },
    );
    const results = JSON.parse(out) as EslintResult[];
    return { exitCode: 0, messages: results.flatMap((r) => r.messages) };
  } catch (err) {
    const e = err as { status?: number; stdout?: string };
    const results = JSON.parse(e.stdout ?? "[]") as EslintResult[];
    return {
      exitCode: e.status ?? 1,
      messages: results.flatMap((r) => r.messages),
    };
  }
}

function expectRuleErrors(messages: EslintMessage[], ruleId: string): void {
  const findings = messages.filter((m) => m.ruleId === ruleId);
  expect(findings.length).toBeGreaterThan(0);
  expect(findings.every((m) => m.severity === SEVERITY_ERROR)).toBe(true);
}

describe("strict type-aware ESLint rules are errors (AE-0446)", () => {
  beforeEach(() => mkdirSync(PROBE_DIR, { recursive: true }));
  afterEach(() => rmSync(PROBE_DIR, { recursive: true, force: true }));

  it(
    "ERRORS on an unnecessary ?? and on || over a nullable value",
    () => {
      writeFileSync(
        PROBE,
        `export function always(value: string): string {\n` +
          `  return value ?? "fallback";\n}\n\n` +
          `export function nullable(value: string | null): string {\n` +
          `  return value || "fallback";\n}\n`,
      );
      const { exitCode, messages } = lintProbe();

      expect(exitCode).not.toBe(0);
      expectRuleErrors(messages, NO_UNNECESSARY_CONDITION);
      expectRuleErrors(messages, PREFER_NULLISH);
    },
    ESLINT_SUBPROCESS_TIMEOUT_MS,
  );
});
