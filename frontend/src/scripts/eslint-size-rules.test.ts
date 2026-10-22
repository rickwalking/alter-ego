/**
 * Rule-fires regression test: the size/complexity rules (max-lines,
 * max-lines-per-function, complexity, max-depth, max-statements and
 * sonarjs/cognitive-complexity) must report severity 2 (error) on seeded
 * violations. Code is linted in memory through the ESLint Node API with a
 * virtual file path under src/, so nothing is written into src/. The virtual
 * path is not in tsconfig, so type-aware parsing is switched off; the size
 * rules are not type-aware and keep the severities and limits of the real config.
 */
import { join } from "node:path";
import { ESLint } from "eslint";
import tseslint from "typescript-eslint";
import { describe, expect, it } from "vitest";

const FRONTEND_ROOT = join(import.meta.dirname, "..", "..");
const PROBE_TS = join(
  FRONTEND_ROOT,
  "src",
  "modules",
  "__size_probe__",
  "probe.ts",
);
const PROBE_TSX = join(
  FRONTEND_ROOT,
  "src",
  "modules",
  "__size_probe__",
  "probe.tsx",
);
const SEVERITY_ERROR = 2;
const SIZE_RULES = [
  "max-lines",
  "max-lines-per-function",
  "complexity",
  "max-depth",
  "max-statements",
  "sonarjs/cognitive-complexity",
] as const;
const FILE_LINES_OVER_TS = 410;
const FILE_LINES_OVER_TSX = 210;
const STATEMENTS_OVER = 60;
const BRANCHES_OVER = 14;
const DEPTH_OVER = 6;
const LINT_TIMEOUT_MS = 120_000;

const eslint = new ESLint({
  cwd: FRONTEND_ROOT,
  overrideConfig: [
    {
      files: ["**/*.ts", "**/*.tsx"],
      languageOptions: { parserOptions: { projectService: false } },
    },
    tseslint.configs.disableTypeChecked,
  ],
});

async function lint(code: string, filePath: string) {
  const [result] = await eslint.lintText(code, { filePath });
  return (result?.messages ?? []).filter(
    (message) =>
      message.ruleId !== null &&
      (SIZE_RULES as readonly string[]).includes(message.ruleId),
  );
}

function repeat(count: number, build: (index: number) => string): string {
  return Array.from({ length: count }, (_, index) => build(index)).join("\n");
}

function nestedIfs(depth: number): string {
  const open = repeat(depth, () => "if (value) {");
  const close = repeat(depth, () => "}");
  return `${open}\nconsole.error(value);\n${close}`;
}

describe("size and complexity ESLint rules", () => {
  // Scenario: an over-long ts file fires max-lines as an error
  it(
    "reports max-lines at severity 2 for a long .ts file",
    async () => {
      const code = repeat(
        FILE_LINES_OVER_TS,
        (i) => `export const v${i} = "x";`,
      );
      const messages = await lint(code, PROBE_TS);
      expect(messages.find((m) => m.ruleId === "max-lines")?.severity).toBe(
        SEVERITY_ERROR,
      );
    },
    LINT_TIMEOUT_MS,
  );

  // Scenario: an over-long tsx file fires its stricter max-lines as an error
  it(
    "reports max-lines at severity 2 for a long .tsx file",
    async () => {
      const code = repeat(
        FILE_LINES_OVER_TSX,
        (i) => `export const v${i} = "x";`,
      );
      const messages = await lint(code, PROBE_TSX);
      expect(messages.find((m) => m.ruleId === "max-lines")?.severity).toBe(
        SEVERITY_ERROR,
      );
    },
    LINT_TIMEOUT_MS,
  );

  // Scenario: a long function fires max-lines-per-function and max-statements
  it(
    "reports max-lines-per-function and max-statements at severity 2",
    async () => {
      const body = repeat(STATEMENTS_OVER, (i) => `const a${i} = "x";`);
      const messages = await lint(
        `export function big() {\n${body}\n}`,
        PROBE_TS,
      );
      for (const rule of ["max-lines-per-function", "max-statements"]) {
        expect(messages.find((m) => m.ruleId === rule)?.severity).toBe(
          SEVERITY_ERROR,
        );
      }
    },
    LINT_TIMEOUT_MS,
  );

  // Scenario: many branches fire complexity as an error
  it(
    "reports complexity at severity 2",
    async () => {
      const body = repeat(
        BRANCHES_OVER,
        (i) => `if (value === "${i}") { return "${i}"; }`,
      );
      const messages = await lint(
        `export function branchy(value: string) {\n${body}\nreturn "none";\n}`,
        PROBE_TS,
      );
      expect(messages.find((m) => m.ruleId === "complexity")?.severity).toBe(
        SEVERITY_ERROR,
      );
    },
    LINT_TIMEOUT_MS,
  );

  // Scenario: deep nesting fires max-depth and cognitive complexity as errors
  it(
    "reports max-depth and sonarjs/cognitive-complexity at severity 2",
    async () => {
      const messages = await lint(
        `export function deep(value: boolean) {\n${nestedIfs(DEPTH_OVER)}\n}`,
        PROBE_TS,
      );
      for (const rule of ["max-depth", "sonarjs/cognitive-complexity"]) {
        expect(messages.find((m) => m.ruleId === rule)?.severity).toBe(
          SEVERITY_ERROR,
        );
      }
    },
    LINT_TIMEOUT_MS,
  );

  // Scenario: a small clean snippet triggers none of the size rules
  it(
    "reports no size rule on a small clean snippet",
    async () => {
      const messages = await lint(
        "export function add(a: number, b: number): number {\n  return a + b;\n}\n",
        PROBE_TS,
      );
      expect(messages).toEqual([]);
    },
    LINT_TIMEOUT_MS,
  );
});
