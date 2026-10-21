/**
 * Rule-fires regression test for the strict ESLint presets: typescript-eslint
 * `strictTypeChecked` + `stylisticTypeChecked` and eslint-plugin-sonarjs
 * `recommended`, all raised to "error" for `**\/*.ts` and `**\/*.tsx`, plus
 * `no-warning-comments`.
 *
 * 1. Every rule that had findings when the presets were enabled gets a seeded
 *    violation in a probe module under a real `src/modules/**` path; the ESLint
 *    CLI must report it at severity 2.
 * 2. `calculateConfigForFile` must resolve every preset rule (minus the size
 *    rules tuned elsewhere and the preset's own "off" entries) to severity 2 for
 *    a production `.ts` and `.tsx` file, and keep the documented test-file
 *    exceptions exact.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { ESLint, type Linter } from "eslint";
import sonarjs from "eslint-plugin-sonarjs";
import tseslint from "typescript-eslint";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

const FRONTEND_ROOT = join(import.meta.dirname, "..", "..");
const ESLINT_BIN = join(
  FRONTEND_ROOT,
  "node_modules",
  "eslint",
  "bin",
  "eslint.js",
);
const PROBE_DIR_NAME = "__eslint_strict_presets_probe__";
const PROBE_DIR_REL = `src/modules/${PROBE_DIR_NAME}`;
const PROBE_DIR = join(FRONTEND_ROOT, PROBE_DIR_REL);
const SEVERITY_OFF = 0;
const SEVERITY_ERROR = 2;
const ESLINT_SUBPROCESS_TIMEOUT_MS = 180_000;
const CONFIG_TIMEOUT_MS = 60_000;
const TS = "ts";
const TSX = "tsx";

/** Size/complexity rules owned by the project's size budget, not the presets. */
const SIZE_RULES = new Set([
  "max-lines-per-function",
  "max-lines",
  "max-statements",
  "complexity",
  "max-depth",
  "sonarjs/cognitive-complexity",
]);

/** Preset rules that are deliberately "off" in test files. */
const TEST_FILE_OFF_RULES = new Set([
  "@typescript-eslint/no-non-null-assertion",
  "sonarjs/no-hardcoded-passwords",
]);

interface RuleSeed {
  rule: string;
  ext: typeof TS | typeof TSX;
  code: string;
}

/** One seeded violation per rule that had findings when the presets landed. */
const SEEDS: readonly RuleSeed[] = [
  {
    rule: "@typescript-eslint/require-await",
    ext: TS,
    code: "export async function probe(): Promise<number> {\n  return 1;\n}\n",
  },
  {
    rule: "sonarjs/prefer-read-only-props",
    ext: TSX,
    code: "interface Props {\n  label: string;\n}\nexport function Probe(props: Props): React.ReactElement {\n  return <span>{props.label}</span>;\n}\n",
  },
  {
    rule: "@typescript-eslint/no-confusing-void-expression",
    ext: TS,
    code: "export function probe(fn: () => void): void {\n  const result = fn();\n  console.warn(result);\n}\n",
  },
  {
    rule: "@typescript-eslint/no-non-null-assertion",
    ext: TS,
    code: "export function probe(value: string | undefined): string {\n  return value!;\n}\n",
  },
  {
    rule: "@typescript-eslint/restrict-template-expressions",
    ext: TS,
    code: "export function probe(flag: boolean): string {\n  return `flag ${flag}`;\n}\n",
  },
  {
    rule: "@typescript-eslint/no-unnecessary-type-assertion",
    ext: TS,
    code: "export function probe(value: string): string {\n  return value as string;\n}\n",
  },
  {
    rule: "@typescript-eslint/consistent-type-definitions",
    ext: TS,
    code: "export type Probe = { label: string };\n",
  },
  {
    rule: "@typescript-eslint/no-empty-function",
    ext: TS,
    code: "export function probe(): void {}\n",
  },
  {
    rule: "@typescript-eslint/no-base-to-string",
    ext: TS,
    code: "export function probe(value: { label: string }): string {\n  return String(value);\n}\n",
  },
  {
    rule: "sonarjs/no-nested-conditional",
    ext: TS,
    code: 'export function probe(a: boolean, b: boolean): string {\n  return a ? "a" : b ? "b" : "c";\n}\n',
  },
  {
    rule: "@typescript-eslint/array-type",
    ext: TS,
    code: "export const probe: Array<string> = [];\n",
  },
  {
    rule: "@typescript-eslint/no-unsafe-return",
    ext: TS,
    code: 'export function probe(): string {\n  return JSON.parse("1");\n}\n',
  },
  {
    rule: "@typescript-eslint/no-unsafe-assignment",
    ext: TS,
    code: 'export const probe: number = JSON.parse("1");\n',
  },
  {
    rule: "@typescript-eslint/no-unsafe-member-access",
    ext: TS,
    code: 'const parsed = JSON.parse("{}");\nexport const probe: unknown = parsed.label;\n',
  },
  {
    rule: "@typescript-eslint/no-unsafe-argument",
    ext: TS,
    code: 'function take(value: string): string {\n  return value;\n}\nexport const probe = take(JSON.parse("1"));\n',
  },
  {
    rule: "@typescript-eslint/no-unsafe-call",
    ext: TS,
    code: 'const parsed = JSON.parse("{}");\nexport const probe: unknown = parsed();\n',
  },
  {
    rule: "sonarjs/no-alphabetical-sort",
    ext: TS,
    code: 'export const probe = ["b", "a"].sort();\n',
  },
  {
    rule: "sonarjs/no-os-command-from-path",
    ext: TS,
    code: 'import { execFileSync } from "node:child_process";\nexport const probe = (): string =>\n  execFileSync("node", ["-v"], { encoding: "utf8" });\n',
  },
  {
    rule: "sonarjs/os-command",
    ext: TS,
    code: 'import { execSync } from "node:child_process";\nexport const probe = (arg: string): string =>\n  execSync("ls " + arg, { encoding: "utf8" });\n',
  },
  {
    rule: "sonarjs/deprecation",
    ext: TS,
    code: "/** @deprecated Use current instead. */\nfunction legacy(): number {\n  return 1;\n}\nexport const probe = legacy();\n",
  },
  {
    rule: "@typescript-eslint/no-deprecated",
    ext: TS,
    code: "/** @deprecated Use current instead. */\nfunction legacy(): number {\n  return 1;\n}\nexport const probe = legacy();\n",
  },
  {
    rule: "@typescript-eslint/no-unnecessary-type-conversion",
    ext: TS,
    code: "export const probe = (value: string): string => String(value);\n",
  },
  {
    rule: "@typescript-eslint/non-nullable-type-assertion-style",
    ext: TS,
    code: "export const probe = (value: string | undefined): string =>\n  value as string;\n",
  },
  {
    rule: "sonarjs/publicly-writable-directories",
    ext: TS,
    code: 'export const probe = "/tmp/probe.txt";\n',
  },
  {
    rule: "sonarjs/pseudo-random",
    ext: TS,
    code: "export const probe = (): number => Math.random();\n",
  },
  {
    rule: "sonarjs/public-static-readonly",
    ext: TS,
    code: "export class Probe {\n  static count = 0;\n}\n",
  },
  {
    rule: "sonarjs/no-clear-text-protocols",
    ext: TS,
    code: 'export const probe = "http://backend.internal:8000";\n',
  },
  {
    rule: "@typescript-eslint/return-await",
    ext: TS,
    code: "export async function probe(\n  load: () => Promise<number>,\n): Promise<number> {\n  try {\n    return load();\n  } catch {\n    return 0;\n  }\n}\n",
  },
  {
    rule: "sonarjs/no-extra-arguments",
    ext: TS,
    code: "const none = (): number => 1;\nexport const probe = none(1);\n",
  },
  {
    rule: "sonarjs/slow-regex",
    ext: TS,
    code: "export const probe = /(a+)+$/;\n",
  },
  {
    rule: "sonarjs/no-nested-template-literals",
    ext: TS,
    code: "export const probe = (a: string): string => `x${`y${a}`}`;\n",
  },
  {
    rule: "@typescript-eslint/prefer-regexp-exec",
    ext: TS,
    code: "export const probe = (value: string): RegExpMatchArray | null =>\n  value.match(/a/);\n",
  },
  {
    rule: "sonarjs/prefer-regexp-exec",
    ext: TS,
    code: "export const probe = (value: string): RegExpMatchArray | null =>\n  value.match(/a/);\n",
  },
  {
    rule: "@typescript-eslint/no-inferrable-types",
    ext: TS,
    code: "export function probe(): number {\n  const count: number = 1;\n  return count;\n}\n",
  },
  {
    rule: "@typescript-eslint/only-throw-error",
    ext: TS,
    code: 'export function probe(): never {\n  throw "boom";\n}\n',
  },
  {
    rule: "@typescript-eslint/no-dynamic-delete",
    ext: TS,
    code: "export function probe(map: Record<string, number>, key: string): void {\n  delete map[key];\n}\n",
  },
  {
    rule: "sonarjs/single-character-alternation",
    ext: TS,
    code: "export const probe = /a|b/;\n",
  },
  {
    rule: "sonarjs/anchor-precedence",
    ext: TS,
    code: "export const probe = /ab|cd$/;\n",
  },
  {
    rule: "@typescript-eslint/no-meaningless-void-operator",
    ext: TS,
    code: "export function probe(fn: () => void): void {\n  void fn();\n}\n",
  },
  {
    rule: "sonarjs/void-use",
    ext: TS,
    code: "export function probe(value: number): void {\n  void value;\n}\n",
  },
  {
    rule: "@typescript-eslint/no-misused-spread",
    ext: TS,
    code: 'export const probe = { ...["a", "b"] };\n',
  },
  {
    rule: "sonarjs/no-nested-functions",
    ext: TS,
    code: "export const probe = () => () => () => () => () => () => 1;\n",
  },
  {
    rule: "@typescript-eslint/restrict-plus-operands",
    ext: TS,
    code: "export const probe = (a: number, b: string): string => a + b;\n",
  },
  {
    rule: "@typescript-eslint/no-redundant-type-constituents",
    ext: TS,
    code: "export type Probe = unknown | string;\n",
  },
  {
    rule: "sonarjs/no-nested-assignment",
    ext: TS,
    code: "export function probe(map: Record<string, number[] | undefined>): void {\n  (map.a ??= []).push(1);\n}\n",
  },
  {
    rule: "sonarjs/no-empty-collection",
    ext: TS,
    code: "export function probe(): number | undefined {\n  const items: number[] = [];\n  return items.shift();\n}\n",
  },
  {
    rule: "sonarjs/no-unused-vars",
    ext: TS,
    code: "export function probe(): number {\n  const unused = 1;\n  return 2;\n}\n",
  },
  {
    rule: "@typescript-eslint/no-unnecessary-type-arguments",
    ext: TS,
    code: 'function identity<T = string>(value: T): T {\n  return value;\n}\nexport const probe = identity<string>("a");\n',
  },
  {
    rule: "sonarjs/no-hardcoded-passwords",
    ext: TS,
    code: 'export const ADMIN_PASSWORD = "TestPass123!";\n',
  },
  {
    rule: "@typescript-eslint/prefer-promise-reject-errors",
    ext: TS,
    code: 'export const probe = (): Promise<never> => Promise.reject("boom");\n',
  },
  {
    rule: "sonarjs/unused-import",
    ext: TS,
    code: 'import { join } from "node:path";\nexport const probe = 1;\n',
  },
  {
    rule: "sonarjs/function-return-type",
    ext: TS,
    code: 'export function probe(flag: boolean): string | number {\n  if (flag) {\n    return "a";\n  }\n  return 1;\n}\n',
  },
  {
    rule: "sonarjs/redundant-type-aliases",
    ext: TS,
    code: "export type Probe = string;\n",
  },
  {
    rule: "sonarjs/todo-tag",
    ext: TS,
    code: "// TODO: probe\nexport const probe = 1;\n",
  },
  {
    rule: "no-warning-comments",
    ext: TS,
    code: "// FIXME: probe\nexport const probe = 1;\n",
  },
];

interface EslintMessage {
  ruleId: string | null;
  severity: number;
}
interface EslintResult {
  filePath: string;
  messages: EslintMessage[];
}

function seedFileName(seed: RuleSeed, index: number): string {
  return `seed-${String(index)}.${seed.ext}`;
}

function lintProbeDir(): EslintResult[] {
  try {
    const out = execFileSync(
      process.execPath,
      [ESLINT_BIN, "--format", "json", PROBE_DIR_REL],
      {
        cwd: FRONTEND_ROOT,
        encoding: "utf8",
        stdio: ["pipe", "pipe", "pipe"],
        maxBuffer: 64 * 1024 * 1024,
      },
    );
    return JSON.parse(out) as EslintResult[];
  } catch (err) {
    const e = err as { stdout?: string };
    return JSON.parse(e.stdout ?? "[]") as EslintResult[];
  }
}

function severityOf(entry: Linter.RuleEntry | undefined): number {
  const level = Array.isArray(entry) ? entry[0] : entry;
  if (level === "error") return SEVERITY_ERROR;
  if (level === "warn") return 1;
  if (level === "off" || level === undefined) return SEVERITY_OFF;
  return level;
}

function sonarRecommendedRules(): Partial<Linter.RulesRecord> {
  const recommended = sonarjs.configs?.recommended;
  if (!recommended || Array.isArray(recommended) || !("rules" in recommended)) {
    throw new Error("eslint-plugin-sonarjs has no recommended config");
  }
  return recommended.rules ?? {};
}

function enabledPresetRules(): string[] {
  const presetEntries: Record<string, Linter.RuleEntry> = {};
  for (const config of [
    ...tseslint.configs.strictTypeChecked,
    ...tseslint.configs.stylisticTypeChecked,
  ]) {
    Object.assign(presetEntries, config.rules ?? {});
  }
  Object.assign(presetEntries, sonarRecommendedRules());
  return Object.entries(presetEntries)
    .filter(([rule, entry]) => !SIZE_RULES.has(rule) && severityOf(entry) > 0)
    .map(([rule]) => rule);
}

async function resolvedRules(
  relPath: string,
): Promise<Partial<Linter.RulesRecord>> {
  const eslint = new ESLint({ cwd: FRONTEND_ROOT });
  const config = (await eslint.calculateConfigForFile(relPath)) as {
    rules?: Partial<Linter.RulesRecord>;
  };
  return config.rules ?? {};
}

function nonErrorRules(
  rules: Partial<Linter.RulesRecord>,
  expected: readonly string[],
): string[] {
  return expected.filter((rule) => severityOf(rules[rule]) !== SEVERITY_ERROR);
}

describe("strict ESLint presets fire on seeded violations", () => {
  let results: EslintResult[] = [];

  beforeAll(() => {
    rmSync(PROBE_DIR, { recursive: true, force: true });
    mkdirSync(PROBE_DIR, { recursive: true });
    SEEDS.forEach((seed, index) => {
      writeFileSync(join(PROBE_DIR, seedFileName(seed, index)), seed.code);
    });
    results = lintProbeDir();
  }, ESLINT_SUBPROCESS_TIMEOUT_MS);

  afterAll(() => {
    rmSync(PROBE_DIR, { recursive: true, force: true });
  });

  it.each(SEEDS.map((seed, index) => ({ ...seed, index })))(
    "$rule errors on its seeded violation",
    ({ rule, index, ext }) => {
      const fileName = seedFileName({ rule, ext, code: "" }, index);
      const result = results.find((r) => r.filePath.endsWith(fileName));
      const findings = (result?.messages ?? []).filter(
        (m) => m.ruleId === rule,
      );
      expect(findings.length).toBeGreaterThan(0);
      expect(findings.every((m) => m.severity === SEVERITY_ERROR)).toBe(true);
    },
  );
});

describe("strict ESLint presets resolve to error", () => {
  const expected = enabledPresetRules();

  it("covers a non-trivial preset rule set", () => {
    expect(expected.length).toBeGreaterThan(100);
  });

  it.each(["src/modules/probe.ts", "src/modules/probe.tsx"])(
    "every preset rule is an error for production file %s",
    async (relPath) => {
      const rules = await resolvedRules(relPath);
      expect(nonErrorRules(rules, expected)).toEqual([]);
      expect(severityOf(rules["no-warning-comments"])).toBe(SEVERITY_ERROR);
    },
    CONFIG_TIMEOUT_MS,
  );

  it(
    "keeps only the documented exceptions in test files",
    async () => {
      const rules = await resolvedRules("src/modules/probe.test.ts");
      const relaxed = nonErrorRules(rules, expected);
      expect([...relaxed].sort((a, b) => a.localeCompare(b))).toEqual(
        [...TEST_FILE_OFF_RULES].sort((a, b) => a.localeCompare(b)),
      );
      for (const rule of TEST_FILE_OFF_RULES) {
        expect(severityOf(rules[rule])).toBe(SEVERITY_OFF);
      }
      expect(rules["@typescript-eslint/prefer-promise-reject-errors"]).toEqual([
        SEVERITY_ERROR,
        { allowThrowingUnknown: true },
      ]);
    },
    CONFIG_TIMEOUT_MS,
  );
});
