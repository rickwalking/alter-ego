/**
 * AE-0324: the noUncheckedIndexedAccess gate. Rule-fires standard (AE-0180):
 * a SEEDED unguarded `Record[key]` access in a sandbox project FAILS the real
 * checker (real tsc run), and the pure baseline comparator blocks new/grown
 * errors. The real-tree pass is exercised by `npm run lint` (lint:strict-index
 * is in the chain), so no duplicate full-tree tsc run here.
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { evaluateStrictIndex } from "../../scripts/check-strict-index.mjs";

const FRONTEND_ROOT = join(import.meta.dirname, "..", "..");
const SCRIPT = join(FRONTEND_ROOT, "scripts", "check-strict-index.mjs");

// The AE-0295 crash shape: destructuring an unguarded Record lookup.
const SEEDED_VIOLATION = `
const colors: Record<string, { bg: string }> = { a: { bg: "x" } };
const { bg } = colors["missing-key"];
export const seeded = bg;
`;

const CLEAN_SOURCE = `
const colors: Record<string, { bg: string }> = { a: { bg: "x" } };
export const safe = colors["a"]?.bg ?? "fallback";
`;

const SANDBOX_TSCONFIG = JSON.stringify({
  compilerOptions: {
    strict: true,
    noUncheckedIndexedAccess: true,
    noEmit: true,
    skipLibCheck: true,
  },
  include: ["*.ts"],
});

function runChecker(dir: string): { status: number; output: string } {
  try {
    const output = execFileSync("node", [SCRIPT], {
      encoding: "utf8",
      env: {
        ...process.env,
        STRICT_INDEX_PROJECT: join(dir, "tsconfig.json"),
        STRICT_INDEX_BASELINE: join(dir, "baseline.json"),
      },
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

describe("strict-index gate end-to-end (AE-0324, real tsc)", () => {
  let dir: string;
  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "strict-index-"));
    writeFileSync(join(dir, "tsconfig.json"), SANDBOX_TSCONFIG);
    writeFileSync(join(dir, "baseline.json"), '{ "count": 0, "files": {} }');
  });
  afterEach(() => rmSync(dir, { recursive: true, force: true }));

  // Scenario: the gate FIRES on a seeded unguarded Record[key] access
  it("fails on a seeded unguarded indexed access in an enforced path", () => {
    writeFileSync(join(dir, "seeded.ts"), SEEDED_VIOLATION);

    const { status, output } = runChecker(dir);

    expect(status).toBe(1);
    expect(output).toContain("seeded.ts");
    expect(output).toContain("NEW:");
  });

  // Scenario: guarded access passes (control)
  it("passes when indexed access is guarded", () => {
    writeFileSync(join(dir, "clean.ts"), CLEAN_SOURCE);

    const { status, output } = runChecker(dir);

    expect(status).toBe(0);
    expect(output).toContain("OK — no new unchecked indexed access.");
  });

  // Scenario: a baselined legacy file is tolerated at its recorded count
  it("tolerates a baselined file at its recorded error count", () => {
    writeFileSync(join(dir, "legacy.ts"), SEEDED_VIOLATION);
    writeFileSync(
      join(dir, "baseline.json"),
      JSON.stringify({ count: 1, files: { "legacy.ts": 1 } }),
    );

    const { status } = runChecker(dir);

    expect(status).toBe(0);
  });
});

describe("strict-index baseline generator is down-only per file (QA F-2)", () => {
  const GENERATOR = join(
    FRONTEND_ROOT,
    "scripts",
    "generate-strict-index-baseline.mjs",
  );

  function runGenerator(dir: string): { status: number; output: string } {
    try {
      const output = execFileSync("node", [GENERATOR], {
        encoding: "utf8",
        env: {
          ...process.env,
          STRICT_INDEX_PROJECT: join(dir, "tsconfig.json"),
          STRICT_INDEX_BASELINE: join(dir, "baseline.json"),
        },
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

  let dir: string;
  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "strict-index-gen-"));
    writeFileSync(join(dir, "tsconfig.json"), SANDBOX_TSCONFIG);
  });
  afterEach(() => rmSync(dir, { recursive: true, force: true }));

  // Scenario: a shrinking TOTAL must not absorb a NEW file's errors
  it("refuses to absorb a new-file error even when the total shrinks", () => {
    // Baseline tolerates 2 errors in legacy.ts; tree now has 1 in legacy.ts
    // (one fixed) + 1 in a NEW file -> total 2 <= 2, but NEW must refuse.
    writeFileSync(
      join(dir, "legacy.ts"),
      `${SEEDED_VIOLATION}\nconst m: Record<string, number> = {};\nexport const second = m["k"] + seeded.length;\n`,
    );
    writeFileSync(
      join(dir, "baseline.json"),
      JSON.stringify({ count: 3, files: { "legacy.ts": 3 } }),
    );
    writeFileSync(
      join(dir, "fresh.ts"),
      SEEDED_VIOLATION.replace("seeded", "fresh"),
    );

    const { status, output } = runGenerator(dir);

    expect(status).toBe(1);
    expect(output).toContain("REFUSED");
    expect(output).toContain("NEW: fresh.ts");
  });

  it("writes a genuinely ratcheted-down baseline", () => {
    writeFileSync(join(dir, "legacy.ts"), SEEDED_VIOLATION);
    writeFileSync(
      join(dir, "baseline.json"),
      JSON.stringify({ count: 3, files: { "legacy.ts": 3 } }),
    );

    const { status, output } = runGenerator(dir);

    expect(status).toBe(0);
    expect(output).toContain("baseline written");
  });
});

describe("strict-index baseline comparator (AE-0324)", () => {
  const baseline = { count: 3, files: { "src/legacy.ts": 3 } };

  it("flags errors in a file outside the baseline", () => {
    const { violations } = evaluateStrictIndex(
      { "src/new-file.ts": 1, "src/legacy.ts": 3 },
      baseline,
    );
    expect(
      violations.some((v: string) => v.startsWith("NEW: src/new-file.ts")),
    ).toBe(true);
  });

  it("flags a baselined file whose count grew", () => {
    const { violations } = evaluateStrictIndex(
      { "src/legacy.ts": 4 },
      baseline,
    );
    expect(
      violations.some((v: string) => v.startsWith("GREW: src/legacy.ts")),
    ).toBe(true);
    expect(violations.some((v: string) => v.startsWith("TOTAL:"))).toBe(true);
  });

  it("passes at exactly the baseline", () => {
    const { violations, total } = evaluateStrictIndex(
      { "src/legacy.ts": 3 },
      baseline,
    );
    expect(violations).toEqual([]);
    expect(total).toBe(3);
  });

  it("passes below the baseline (ratchet-down candidate)", () => {
    const { violations, total } = evaluateStrictIndex(
      { "src/legacy.ts": 1 },
      baseline,
    );
    expect(violations).toEqual([]);
    expect(total).toBe(1);
  });
});
