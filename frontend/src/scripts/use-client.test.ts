/**
 * AE-0166: the use-client static check — a .tsx component calling client-only
 * React hooks must declare "use client". Passes on the real tree; ERRORS on a
 * seeded violation.
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

const FRONTEND_ROOT = join(import.meta.dirname, "..", "..");
const SCRIPT = join(FRONTEND_ROOT, "scripts", "check-use-client.mjs");

function run(root?: string): { status: number; output: string } {
  try {
    const output = execFileSync("node", [SCRIPT], {
      cwd: FRONTEND_ROOT,
      encoding: "utf8",
      env: { ...process.env, ...(root ? { USE_CLIENT_ROOT: root } : {}) },
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

describe("use-client static check (AE-0166)", () => {
  let dir: string;
  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "use-client-"));
  });
  afterEach(() => rmSync(dir, { recursive: true, force: true }));

  it("passes on the real source tree (all client components declare the directive)", () => {
    const { status, output } = run();
    expect(status, output).toBe(0);
    expect(output).toContain("use-client check OK");
  });

  it("FAILS on a component using a client hook without the directive", () => {
    writeFileSync(
      join(dir, "bad.tsx"),
      `import { useState } from "react";\nexport function Bad(){ const [x]=useState(0); return null; }\n`,
    );
    const { status, output } = run(dir);
    expect(status, output).not.toBe(0);
    expect(output).toContain('Missing "use client"');
  });

  it("passes when the directive is present", () => {
    writeFileSync(
      join(dir, "good.tsx"),
      `"use client";\nimport { useState } from "react";\nexport function Good(){ const [x]=useState(0); return null; }\n`,
    );
    const { status, output } = run(dir);
    expect(status, output).toBe(0);
  });

  it("passes when the directive follows a leading comment block (M2 fix)", () => {
    writeFileSync(
      join(dir, "licensed.tsx"),
      `/**\n * @file licensed component\n */\n"use client";\n` +
        `import { useState } from "react";\nexport function C(){ const [x]=useState(0); return null; }\n`,
    );
    const { status, output } = run(dir);
    expect(status, output).toBe(0);
  });

  it("does not flag a hook name that appears only in a comment (L1 fix)", () => {
    writeFileSync(
      join(dir, "commented.tsx"),
      `// historically this used useState before refactor\n` +
        `export function Pure(){ return null; }\n`,
    );
    const { status, output } = run(dir);
    expect(status, output).toBe(0);
  });

  it("ignores non-component files (a hook .ts module is not flagged)", () => {
    mkdirSync(join(dir, "hooks"));
    writeFileSync(
      join(dir, "hooks", "use-thing.ts"),
      `import { useState } from "react";\nexport function useThing(){ return useState(0); }\n`,
    );
    // .ts files are out of scope (only .tsx components are checked).
    const { status } = run(dir);
    expect(status).toBe(0);
  });
});
