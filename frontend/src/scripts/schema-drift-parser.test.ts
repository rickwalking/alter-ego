/**
 * AE-0323: the schema-drift checker parses Zod literals via the TS compiler
 * API. Rule-fires standard (AE-0180): the comment false-positive is seeded and
 * must NOT fire; genuine drift is seeded and MUST fire; string/template/regex
 * shapes must not create false negatives. The real script stays green on the
 * real tree (control, exercised by the lint gate itself).
 */
import { execFileSync } from "node:child_process";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import {
  classifyZodExpr,
  compareFields,
  extractZodObjectFields,
} from "../../scripts/check-schema-drift.mjs";

const FRONTEND_ROOT = join(import.meta.dirname, "..", "..");
const SCRIPT = join(FRONTEND_ROOT, "scripts", "check-schema-drift.mjs");

type ZodFieldSpec = { type: string; nullable: boolean; optional: boolean };

function fieldMap(
  source: string,
  constName: string,
): Record<string, ZodFieldSpec> {
  const fields = extractZodObjectFields(source, constName);
  expect(fields).not.toBeNull();
  const out: Record<string, ZodFieldSpec> = {};
  for (const { name, expr } of fields ?? []) {
    out[name] = classifyZodExpr(expr) as ZodFieldSpec;
  }
  return out;
}

describe("schema-drift Zod parsing via TS compiler API (AE-0323)", () => {
  // Scenario: the AE-0298 incident — inline comments are NOT fields
  it("ignores line and block comments inside the object literal", () => {
    const source = `
export const s = z.object({
  // AE-0298 — this line was misread as a field by the old char-walk
  topic: z.string(),
  /* block comment, with: colon and , comma */
  audience: z.string().optional(), // trailing comment
});
`;
    const fields = extractZodObjectFields(source, "s") ?? [];
    expect(fields.map((f) => f.name)).toEqual(["topic", "audience"]);
  });

  // Scenario: string contents cannot corrupt field extraction (false-negative
  // guard, cold-critic WARN-3)
  it("handles strings, template literals, and regex literals in values", () => {
    const source = `
export const s = z.object({
  url: z.string().regex(/https?:\\/\\/[^,{]+/),
  label: z.string().default("a, b: {c}"),
  note: z.string().default(\`multi
line \${"x, y"} template // not a comment\`),
  count: z.number(),
});
`;
    const fields = extractZodObjectFields(source, "s") ?? [];
    expect(fields.map((f) => f.name)).toEqual([
      "url",
      "label",
      "note",
      "count",
    ]);
  });

  it("extracts quoted and nested keys correctly", () => {
    const source = `
export const s = z.object({
  "quoted-key": z.string(),
  nested: z.object({ inner: z.string(), also: z.number() }),
  tail: z.boolean(),
});
`;
    const fields = fieldMap(source, "s");
    expect(Object.keys(fields)).toEqual(["quoted-key", "nested", "tail"]);
    expect(fields["nested"]?.type).toBe("object");
  });

  it("targets the named const, not another schema in the same file", () => {
    const source = `
export const other = z.object({ wrong: z.string() });
export const target = z.object({ right: z.string() });
`;
    const fields = extractZodObjectFields(source, "target") ?? [];
    expect(fields.map((f) => f.name)).toEqual(["right"]);
  });

  it("returns null when the const has no z.object literal", () => {
    expect(extractZodObjectFields("export const s = 42;", "s")).toBeNull();
    expect(extractZodObjectFields("const unrelated = 1;", "s")).toBeNull();
  });
});

describe("schema-drift comparison still fires on seeded drift (AE-0180)", () => {
  const component = {
    properties: {
      topic: { type: "string" },
      audience: { anyOf: [{ type: "string" }, { type: "null" }] },
    },
    required: ["topic"],
  };

  it("flags a frontend-only field (EXTRA-FRONTEND-FIELD)", () => {
    const zod = fieldMap(
      `export const s = z.object({
  topic: z.string(),
  audience: z.string().nullable(),
  ghost: z.string(), // seeded drift: not in the API schema
});`,
      "s",
    );
    const findings = compareFields(zod, component);
    expect(
      findings.some((f: string) => f.includes('EXTRA-FRONTEND-FIELD: "ghost"')),
    ).toBe(true);
  });

  it("flags a missing required API field (MISSING-REQUIRED-FIELD)", () => {
    const zod = fieldMap(
      `export const s = z.object({ audience: z.string().nullable() });`,
      "s",
    );
    const findings = compareFields(zod, component);
    expect(
      findings.some((f: string) =>
        f.includes('MISSING-REQUIRED-FIELD: API field "topic"'),
      ),
    ).toBe(true);
  });

  it("flags a type mismatch (TYPE-MISMATCH)", () => {
    const zod = fieldMap(
      `export const s = z.object({
  topic: z.number(), // seeded drift: API says string
  audience: z.string().nullable(),
});`,
      "s",
    );
    const findings = compareFields(zod, component);
    expect(
      findings.some((f: string) => f.includes('TYPE-MISMATCH: "topic"')),
    ).toBe(true);
  });

  it("reports clean when fields align despite comments", () => {
    const zod = fieldMap(
      `export const s = z.object({
  // comments must not create drift
  topic: z.string(),
  audience: z.string().nullable(),
});`,
      "s",
    );
    expect(compareFields(zod, component)).toEqual(["clean"]);
  });
});

describe("schema-drift script end-to-end (control)", () => {
  it("stays green on the real tree in --strict mode", () => {
    // The gate itself: real schemas vs the committed openapi.json artifact.
    const output = execFileSync("node", [SCRIPT, "--strict"], {
      cwd: FRONTEND_ROOT,
      encoding: "utf8",
    });
    expect(output).toContain("No drift across mapped schemas.");
  });
});
