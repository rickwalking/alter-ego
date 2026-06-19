/**
 * AE-0224 rule-fires regression test (dogfoods AE-0180): a bare magic number in
 * production `src` (outside the ignored small set and the constants/schemas
 * layers) must be an ESLint ERROR (`no-magic-numbers`). The rule was enabled as
 * `error` alongside centralizing API_BASE / HTTP_STATUS; this test proves it
 * actually fires so it cannot silently regress to a warning or get disabled.
 *
 * The probe is a real `.ts` file under `src/modules` — inside the exact glob the
 * no-magic-numbers config block targets (and which the constants/test ignores do
 * NOT exempt) — then linted via the ESLint CLI.
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
  "__eslint_magic_probe__",
);
const PROBE_REL = "src/modules/__eslint_magic_probe__/probe.ts";
const PROBE = join(FRONTEND_ROOT, PROBE_REL);
const NO_MAGIC_NUMBERS = "no-magic-numbers";
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

describe("no-magic-numbers is an ESLint error (AE-0224)", () => {
  beforeEach(() => mkdirSync(PROBE_DIR, { recursive: true }));
  afterEach(() => rmSync(PROBE_DIR, { recursive: true, force: true }));

  it(
    "ERRORS on a bare magic number in production src",
    () => {
      // 8080 is outside the ignored set (-1, 0, 1, 2, 100); not an array index,
      // default value, or enum — a clear magic-number violation.
      writeFileSync(
        PROBE,
        `export function probe(): number {\n` + `  return 8080 * 3;\n` + `}\n`,
      );
      const { exitCode, results } = lintProbe();
      const findings = results
        .flatMap((r) => r.messages)
        .filter((m) => m.ruleId === NO_MAGIC_NUMBERS);

      expect(exitCode).not.toBe(0);
      expect(findings.length).toBeGreaterThan(0);
      expect(findings.every((m) => m.severity === SEVERITY_ERROR)).toBe(true);
    },
    ESLINT_SUBPROCESS_TIMEOUT_MS,
  );
});
