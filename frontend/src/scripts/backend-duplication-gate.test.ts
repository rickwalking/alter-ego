/**
 * Rule-fires tests for the backend jscpd gate (`gates.sh backend:duplication`,
 * config `backend/.jscpd.json`). They live here because the backend gate
 * reuses this package's jscpd binary, which the backend test job does not
 * install.
 *
 * Scenario: two files share a 30-line identical function -> non-zero exit
 * Scenario: two files hold distinct code -> zero exit
 * Scenario: module facade files mirror each other -> excluded, zero exit
 */
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

const FRONTEND_ROOT = join(import.meta.dirname, "..", "..");
const JSCPD_BIN = join(FRONTEND_ROOT, "node_modules", ".bin", "jscpd");
const BACKEND_CONFIG = join(FRONTEND_ROOT, "..", "backend", ".jscpd.json");
const SEEDED_LINES = 30;

function pythonFunction(name: string, salt: string): string {
  const body = Array.from(
    { length: SEEDED_LINES - 3 },
    (_, index) =>
      `    total += values[${String(index)}] * ${String(index + 2)} + len('${salt}${String(index)}')`,
  );
  return [
    `def ${name}(values: list[int]) -> int:`,
    "    total = 0",
    ...body,
    "    return total",
    "",
  ].join("\n");
}

function scan(sourceDir: string): { status: number | null; output: string } {
  const result = spawnSync(JSCPD_BIN, [sourceDir, "--config", BACKEND_CONFIG], {
    cwd: join(sourceDir, ".."),
    encoding: "utf8",
  });
  return { status: result.status, output: result.stdout + result.stderr };
}

const seeded: string[] = [];

function seedDir(...segments: string[]): string {
  const root = mkdtempSync(join(tmpdir(), "backend-dup-"));
  seeded.push(root);
  const dir = join(root, "src", ...segments);
  mkdirSync(dir, { recursive: true });
  return dir;
}

afterEach(() => {
  seeded.splice(0).forEach((dir) => {
    rmSync(dir, { recursive: true, force: true });
  });
});

describe("backend duplication gate", () => {
  it("fails when two files share a 30-line identical function", () => {
    // Scenario: two files share a 30-line identical function -> non-zero exit
    const src = seedDir();
    const shared = pythonFunction("compute", "same");
    writeFileSync(join(src, "first.py"), shared);
    writeFileSync(join(src, "second.py"), shared);

    const result = scan(src);

    expect(result.status, result.output).not.toBe(0);
    expect(result.output).toContain("Found 1 clones");
  });

  it("passes on distinct code", () => {
    // Scenario: two files hold distinct code -> zero exit
    const src = seedDir();
    writeFileSync(join(src, "first.py"), pythonFunction("alpha", "one"));
    writeFileSync(
      join(src, "second.py"),
      "def beta(text: str) -> str:\n    return text.strip().lower()\n",
    );

    const result = scan(src);

    expect(result.status, result.output).toBe(0);
    expect(result.output).toContain("Found 0 clones");
  });

  it("excludes the module facade files", () => {
    // Scenario: module facade files mirror each other -> excluded, zero exit
    const facade = seedDir("pkg", "modules", "billing");
    const shared = pythonFunction("compute", "same");
    writeFileSync(join(facade, "__init__.py"), shared);
    writeFileSync(join(facade, "public.py"), shared);

    const result = scan(join(facade, "..", "..", ".."));

    expect(result.status, result.output).toBe(0);
  });
});
