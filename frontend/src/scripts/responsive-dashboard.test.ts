/**
 * AE-0277: rule-fires regression test for the responsive-dashboard gate.
 * Proves each detection branch FIRES on a seeded violation (AE-0180), the false-
 * positive guards hold, the allow-list is in sync, and the real tree passes.
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  findViolations,
  ALLOW_LIST,
} from "../../scripts/check-responsive-dashboard.mjs";

const FRONTEND_ROOT = join(import.meta.dirname, "..", "..");
const SCRIPT = join(FRONTEND_ROOT, "scripts", "check-responsive-dashboard.mjs");

function runCli(files?: string[]): { status: number; output: string } {
  try {
    const output = execFileSync("node", [SCRIPT], {
      cwd: FRONTEND_ROOT,
      encoding: "utf8",
      env: {
        ...process.env,
        ...(files ? { RESPONSIVE_DASHBOARD_FILES: files.join(",") } : {}),
      },
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

const rules = (src: string): string[] =>
  findViolations(src, "fixture.tsx").map((v) => v.rule);

describe("responsive-dashboard gate (AE-0277)", () => {
  it("passes on the real dashboard tree", () => {
    const { status, output } = runCli();
    expect(status, output).toBe(0);
    expect(output).toContain("responsive-dashboard check OK");
  });

  it("every allow-listed file exists (allow-list in sync)", () => {
    for (const rel of ALLOW_LIST) {
      expect(existsSync(join(FRONTEND_ROOT, rel)), rel).toBe(true);
    }
  });

  // Branch A — frozen grid
  it("FIRES on inline gridTemplateColumns", () => {
    const src = `<div style={{ display: "grid", gridTemplateColumns: "1fr 360px" }} />`;
    expect(rules(src)).toContain("gridTemplateColumns");
  });

  // Branch B — frozen shell offset
  it("FIRES on px marginLeft >= 64", () => {
    expect(rules(`<div style={{ marginLeft: 240 }} />`)).toContain(
      "marginLeft",
    );
    expect(rules(`<div style={{ marginLeft: "240px" }} />`)).toContain(
      "marginLeft",
    );
  });

  it("does NOT fire on small spacing marginLeft (false-positive guard)", () => {
    expect(rules(`<div style={{ marginLeft: 8 }} />`)).not.toContain(
      "marginLeft",
    );
    expect(rules(`<div style={{ marginLeft: "6px" }} />`)).not.toContain(
      "marginLeft",
    );
  });

  // Branch C — frozen pane width on a layout container
  it("FIRES on fixed width >= 200px on a flex/grid container", () => {
    const src = `<div style={{ display: "flex", width: "280px" }} />`;
    expect(rules(src)).toContain("layout-width");
  });

  it("does NOT fire on small widths or non-layout widths (false-positive guard)", () => {
    // small leaf width (avatar) with flex centering
    expect(
      rules(`<div style={{ display: "flex", width: "36px" }} />`),
    ).not.toContain("layout-width");
    // wide width but not a flex/grid container
    expect(rules(`<div style={{ width: "280px" }} />`)).not.toContain(
      "layout-width",
    );
  });

  // End-to-end: a seeded violation file makes the CLI exit non-zero.
  it("CLI exits non-zero on a seeded violation file", () => {
    const dir = mkdtempSync(join(tmpdir(), "resp-dash-"));
    const file = join(dir, "bad.tsx");
    writeFileSync(
      file,
      `export const X = () => <div style={{ gridTemplateColumns: "1fr 1fr" }} />;\n`,
    );
    const { status, output } = runCli([file]);
    rmSync(dir, { recursive: true, force: true });
    expect(status, output).not.toBe(0);
    expect(output).toContain("responsive-dashboard check FAILED");
  });
});
