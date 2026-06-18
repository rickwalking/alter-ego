/**
 * AE-0226 rule-fires regression test (dogfoods AE-0180): an `else` block after a
 * returning `if` in production `src` must be an ESLint ERROR (`no-else-return`),
 * not a warning. The early-return / guard-clause rule was enabled as `error`
 * (AE-0147); this test proves it actually fires so it cannot silently regress to
 * a warning or get disabled.
 *
 * A probe module is written under a real `src/modules/**` path so it is matched
 * by the flat config + tsconfig project, then linted via the ESLint CLI.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

const FRONTEND_ROOT = join(import.meta.dirname, "..", "..");
const PROBE_DIR = join(
  FRONTEND_ROOT,
  "src",
  "modules",
  "__eslint_else_probe__",
);
const PROBE_REL = "src/modules/__eslint_else_probe__/probe.ts";
const PROBE = join(FRONTEND_ROOT, PROBE_REL);
const NO_ELSE_RETURN = "no-else-return";
const SEVERITY_ERROR = 2;
const ESLINT_SUBPROCESS_TIMEOUT_MS = 60_000;

interface EslintMessage {
  ruleId: string | null;
  severity: number;
}
interface EslintResult {
  messages: EslintMessage[];
}

function lintProbe(): { exitCode: number; results: EslintResult[] } {
  try {
    const out = execFileSync("npx", ["eslint", "--format", "json", PROBE_REL], {
      cwd: FRONTEND_ROOT,
      encoding: "utf8",
      stdio: ["pipe", "pipe", "pipe"],
    });
    return { exitCode: 0, results: JSON.parse(out) as EslintResult[] };
  } catch (err) {
    const e = err as { status?: number; stdout?: string };
    return {
      exitCode: e.status ?? 1,
      results: JSON.parse(e.stdout ?? "[]") as EslintResult[],
    };
  }
}

describe("no-else-return is an ESLint error (AE-0226)", () => {
  beforeEach(() => mkdirSync(PROBE_DIR, { recursive: true }));
  afterEach(() => rmSync(PROBE_DIR, { recursive: true, force: true }));

  it(
    "ERRORS on an else block after a returning if in production src",
    () => {
      writeFileSync(
        PROBE,
        `export function probe(flag: boolean): string {\n` +
          `  if (flag) {\n` +
          `    return "yes";\n` +
          `  } else {\n` +
          `    return "no";\n` +
          `  }\n` +
          `}\n`,
      );
      const { exitCode, results } = lintProbe();
      const findings = results
        .flatMap((r) => r.messages)
        .filter((m) => m.ruleId === NO_ELSE_RETURN);

      expect(exitCode).not.toBe(0);
      expect(findings.length).toBeGreaterThan(0);
      expect(findings.every((m) => m.severity === SEVERITY_ERROR)).toBe(true);
    },
    ESLINT_SUBPROCESS_TIMEOUT_MS,
  );
});
