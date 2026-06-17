/**
 * AE-0179 rule-fires regression test (dogfoods AE-0180) for the ESLint
 * flat-config same-key override guard (scripts/check-eslint-rule-overrides.mjs).
 *
 * Feature: detect a rule key declared across overlapping flat-config objects
 *   Scenario: the REAL config passes (intentional re-declares are allow-listed)
 *   Scenario: a SEEDED unlisted overlapping duplicate FAILS (non-zero exit)
 *   Scenario: the same seeded duplicate PASSES once the rule is allow-listed
 *
 * The guard loads the config + allow-list via ESLINT_OVERRIDE_CONFIG /
 * ESLINT_OVERRIDE_ALLOWLIST so we can point it at throwaway fixtures.
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

const FRONTEND_ROOT = join(import.meta.dirname, "..", "..");
const SCRIPT = join(
  FRONTEND_ROOT,
  "scripts",
  "check-eslint-rule-overrides.mjs",
);
const GUARD_TIMEOUT_MS = 60_000;

function run(env: Record<string, string> = {}): {
  status: number;
  output: string;
} {
  try {
    const output = execFileSync("node", [SCRIPT], {
      cwd: FRONTEND_ROOT,
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

// A config with a global `no-restricted-syntax` ERROR (the H1 flagship rule)
// silently re-declared as a scoped WARN over src/modules — the exact footgun.
const SEEDED_CONFIG = `
export default [
  {
    rules: {
      "no-restricted-syntax": ["error", { selector: "X", message: "global" }],
    },
  },
  {
    files: ["src/modules/**/*.tsx"],
    rules: {
      "no-restricted-syntax": ["warn", { selector: "Y", message: "scoped" }],
    },
  },
];
`;

describe("ESLint rule-override guard (AE-0179)", () => {
  let dir: string;
  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "eslint-override-"));
  });
  afterEach(() => rmSync(dir, { recursive: true, force: true }));

  it(
    "PASSES on the real eslint.config.mjs (intentional re-declares are allow-listed)",
    () => {
      const { status, output } = run();
      expect(status, output).toBe(0);
      expect(output).toContain("0 unlisted collisions");
    },
    GUARD_TIMEOUT_MS,
  );

  it(
    "FAILS on a seeded unlisted overlapping duplicate rule key",
    () => {
      const cfg = join(dir, "config.mjs");
      const allow = join(dir, "allow.json");
      writeFileSync(cfg, SEEDED_CONFIG);
      writeFileSync(allow, JSON.stringify({ allow: {} }));
      const { status, output } = run({
        ESLINT_OVERRIDE_CONFIG: cfg,
        ESLINT_OVERRIDE_ALLOWLIST: allow,
      });
      expect(status, output).not.toBe(0);
      expect(output).toContain("no-restricted-syntax");
      expect(output).toContain("FAILED");
    },
    GUARD_TIMEOUT_MS,
  );

  it(
    "PASSES on the same seeded duplicate once the rule is allow-listed",
    () => {
      const cfg = join(dir, "config.mjs");
      const allow = join(dir, "allow.json");
      writeFileSync(cfg, SEEDED_CONFIG);
      writeFileSync(
        allow,
        JSON.stringify({
          allow: { "no-restricted-syntax": "intentional test re-declare" },
        }),
      );
      const { status, output } = run({
        ESLINT_OVERRIDE_CONFIG: cfg,
        ESLINT_OVERRIDE_ALLOWLIST: allow,
      });
      expect(status, output).toBe(0);
      expect(output).toContain("0 unlisted collisions");
    },
    GUARD_TIMEOUT_MS,
  );
});
