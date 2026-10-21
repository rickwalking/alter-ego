/**
 * Rule-fires regression test for the frontend comment policy gate
 * (scripts/check-comments.mjs): passes on the real tree, ERRORS on a seeded
 * non-doc comment, ticket id or to-do marker, and lets JSDoc, tool directives
 * and Gherkin references through.
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

const FRONTEND_ROOT = join(import.meta.dirname, "..", "..");
const SCRIPT = join(FRONTEND_ROOT, "scripts", "check-comments.mjs");

interface RunResult {
  status: number;
  output: string;
}

function run(root?: string): RunResult {
  try {
    const output = execFileSync(process.execPath, [SCRIPT], {
      cwd: FRONTEND_ROOT,
      encoding: "utf8",
      env: { ...process.env, ...(root ? { COMMENTS_ROOT: root } : {}) },
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

const ESLINT_DISABLE = ["eslint", "disable"].join("-");

const CLEAN = [
  "/** Adds two numbers. */",
  "export function add(a: number, b: number): number {",
  `  // ${ESLINT_DISABLE}-next-line no-console`,
  '  console.log("sum");',
  "  return a + b;",
  "}",
  "// Scenario: A long scenario title that wraps over",
  "//   two comment lines",
  "export const ONE = 1;",
  "",
].join("\n");

const SEEDED: readonly (readonly [string, string, string])[] = [
  ["line comment", "const a = 1;\n// explain a\nexport { a };\n", "non-doc"],
  ["trailing comment", "export const a = 1; // note\n", "non-doc"],
  ["block comment", "/* note */\nexport const a = 1;\n", "non-doc"],
  ["commented-out code", "// const old = compute();\n", "non-doc"],
  [
    "JSX comment",
    "export const C = () => <div>{/* note */}</div>;\n",
    "non-doc",
  ],
  [
    "ticket id in JSDoc",
    "/** Adds (AE-0123). */\nexport const a = 1;\n",
    "ticket",
  ],
  ["decision id in JSDoc", "/** Per D-6. */\nexport const a = 1;\n", "ticket"],
  ["TODO in JSDoc", "/** TODO: drop. */\nexport const a = 1;\n", "TODO"],
];

describe("comment policy check", () => {
  let dir: string;
  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "comments-"));
  });
  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
  });

  it("passes on the real source tree", () => {
    const { status, output } = run();
    expect(status, output).toBe(0);
    expect(output).toContain("comment policy OK");
  });

  it("passes JSDoc, tool directives and Gherkin references", () => {
    writeFileSync(join(dir, "clean.ts"), CLEAN);
    const { status, output } = run(dir);
    expect(status, output).toBe(0);
  });

  it("lets a Gherkin reference repeat a ticket id from the scenario title", () => {
    writeFileSync(
      join(dir, "ref.test.ts"),
      "// Scenario: GLM requests carry the session header (AE-0330)\nexport const a = 1;\n",
    );
    expect(run(dir).status).toBe(0);
  });

  it.each(SEEDED)("FAILS on a seeded %s", (_name, source, reason) => {
    writeFileSync(join(dir, "bad.tsx"), source);
    const { status, output } = run(dir);
    expect(status, output).toBe(1);
    expect(output).toContain(`bad.tsx:`);
    expect(output).toContain(reason);
  });
});
