/**
 * AE-0166 regression: `fetch()` inside `useEffect` must be an ESLint ERROR
 * (not merely a warning) — including in `src/modules`/`src/components`, where a
 * since-removed scoped `no-restricted-syntax` block used to silently override it
 * (ESLint flat config replaces, not merges, same-key rules across objects).
 *
 * The probe is written under a real `src/modules/**` path so it is matched by
 * the flat config + tsconfig project, then linted via the ESLint CLI.
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
  "__eslint_fetch_probe__",
);
const PROBE = join(PROBE_DIR, "probe.tsx");
const NO_RESTRICTED_SYNTAX = "no-restricted-syntax";
const SEVERITY_ERROR = 2;

interface EslintMessage {
  ruleId: string | null;
  severity: number;
}
interface EslintResult {
  messages: EslintMessage[];
}

function lintProbe(): { exitCode: number; results: EslintResult[] } {
  try {
    const out = execFileSync(
      "npx",
      [
        "eslint",
        "--format",
        "json",
        "src/modules/__eslint_fetch_probe__/probe.tsx",
      ],
      { cwd: FRONTEND_ROOT, encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] },
    );
    return { exitCode: 0, results: JSON.parse(out) as EslintResult[] };
  } catch (err) {
    const e = err as { status?: number; stdout?: string };
    return {
      exitCode: e.status ?? 1,
      results: JSON.parse(e.stdout ?? "[]") as EslintResult[],
    };
  }
}

describe("fetch-in-useEffect is an ESLint error (AE-0166)", () => {
  beforeEach(() => mkdirSync(PROBE_DIR, { recursive: true }));
  afterEach(() => rmSync(PROBE_DIR, { recursive: true, force: true }));

  it("ERRORS on fetch() inside useEffect within src/modules", () => {
    writeFileSync(
      PROBE,
      `"use client";\nimport { useEffect } from "react";\n` +
        `export function Probe(): null {\n` +
        `  useEffect(() => {\n    void fetch("/api/x");\n  }, []);\n` +
        `  return null;\n}\n`,
    );
    const { exitCode, results } = lintProbe();
    const restricted = results
      .flatMap((r) => r.messages)
      .filter((m) => m.ruleId === NO_RESTRICTED_SYNTAX);

    expect(exitCode).not.toBe(0);
    expect(restricted.length).toBeGreaterThan(0);
    expect(restricted.every((m) => m.severity === SEVERITY_ERROR)).toBe(true);
  });
});
