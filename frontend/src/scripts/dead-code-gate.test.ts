/**
 * Frontend dead-export gate ratchet logic.
 * Proves the identity-keyed baseline enforcement, including the skeptical-review
 * BLOCKER: a replace-same-count change (remove one grandfathered orphan, add a
 * new one) must FAIL because identity — not count — is the key.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  classifyDeadCode,
  identityKey,
  parseKnipReport,
} from "../../scripts/dead-code-scan.mjs";

function finding(file: string, name: string, type = "export") {
  return { key: identityKey({ type, file, name }), type, file, name, line: 1 };
}

describe("parseKnipReport", () => {
  it("flattens knip issue kinds into type|file|symbol identities", () => {
    const report = {
      issues: [
        {
          file: "src/a.ts",
          exports: [{ name: "Foo", line: 3 }],
          types: [{ name: "Bar", line: 5 }],
        },
      ],
    };
    const findings = parseKnipReport(report);
    expect(findings.map((f: { key: string }) => f.key)).toEqual([
      "export|src/a.ts|Foo",
      "type|src/a.ts|Bar",
    ]);
  });
});

describe("classifyDeadCode", () => {
  const allowed = new Set([
    "export|src/old.ts|GRANDFATHERED",
    "export|src/keep.ts|STILL_UNUSED",
  ]);

  it("blocks a net-new finding in a CHANGED file (day-one blocking)", () => {
    const { blocking, advisory } = classifyDeadCode({
      findings: [finding("src/changed.ts", "NEW_ORPHAN")],
      allowed,
      changedFiles: new Set(["src/changed.ts"]),
    });
    expect(blocking.map((f: { name: string }) => f.name)).toEqual([
      "NEW_ORPHAN",
    ]);
    expect(advisory).toHaveLength(0);
  });

  it("treats a net-new finding in an UNCHANGED file as advisory (non-blocking)", () => {
    const { blocking, advisory } = classifyDeadCode({
      findings: [finding("src/other.ts", "NEW_ORPHAN")],
      allowed,
      changedFiles: new Set(["src/changed.ts"]),
    });
    expect(blocking).toHaveLength(0);
    expect(advisory.map((f: { name: string }) => f.name)).toEqual([
      "NEW_ORPHAN",
    ]);
  });

  it("ignores grandfathered findings", () => {
    const { blocking, advisory } = classifyDeadCode({
      findings: [finding("src/keep.ts", "STILL_UNUSED")],
      allowed,
      changedFiles: new Set(["src/keep.ts"]),
    });
    expect(blocking).toHaveLength(0);
    expect(advisory).toHaveLength(0);
  });

  /** The grandfathered orphan in old.ts is gone and a NEW orphan appears in a changed file: the count is unchanged (1 -> 1) but the gate must still block. */
  it("FAILS a replace-same-count change (identity, not count)", () => {
    const { blocking, resolved } = classifyDeadCode({
      findings: [finding("src/changed.ts", "DIFFERENT_ORPHAN")],
      allowed: new Set(["export|src/old.ts|GRANDFATHERED"]),
      changedFiles: new Set(["src/changed.ts"]),
    });
    expect(blocking.map((f: { name: string }) => f.name)).toEqual([
      "DIFFERENT_ORPHAN",
    ]);
    expect(resolved).toEqual(["export|src/old.ts|GRANDFATHERED"]);
  });

  it("reports resolved grandfathered identities (baseline may ratchet down)", () => {
    const { resolved } = classifyDeadCode({
      findings: [finding("src/keep.ts", "STILL_UNUSED")],
      allowed,
      changedFiles: new Set(),
    });
    expect(resolved).toEqual(["export|src/old.ts|GRANDFATHERED"]);
  });

  it("blocks ALL net-new under fullTreeBlocking (the future flip)", () => {
    const { blocking } = classifyDeadCode({
      findings: [finding("src/unchanged.ts", "NEW_ORPHAN")],
      allowed,
      changedFiles: new Set(),
      fullTreeBlocking: true,
    });
    expect(blocking.map((f: { name: string }) => f.name)).toEqual([
      "NEW_ORPHAN",
    ]);
  });
});

/**
 * The grandfathered baseline reached 0, so the CI gate runs the classifier in
 * full-tree mode. Pin the flip so it cannot silently revert to changed-file-only
 * blocking.
 */
describe("dead-code gate runs full-tree blocking in CI (AE-0446)", () => {
  it("sets DEAD_CODE_FULL_TREE_BLOCKING=1 in the frontend dead-code gate", () => {
    const gates = readFileSync(
      join(import.meta.dirname, "..", "..", "..", "scripts", "ci", "gates.sh"),
      "utf8",
    );
    const gateLine = gates
      .split("\n")
      .find((line) => line.startsWith("gate_frontend_dead_code()"));
    expect(gateLine).toContain(
      "DEAD_CODE_FULL_TREE_BLOCKING=1 npm run lint:dead-code",
    );
  });

  it("keeps the grandfathered baseline empty", () => {
    const baseline = JSON.parse(
      readFileSync(
        join(
          import.meta.dirname,
          "..",
          "..",
          "scripts",
          "dead-code-baseline.json",
        ),
        "utf8",
      ),
    ) as { allowlist?: string[] };
    expect(baseline.allowlist ?? []).toEqual([]);
  });
});
