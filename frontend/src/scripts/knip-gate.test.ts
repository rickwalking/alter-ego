/**
 * Full knip gate (`npm run lint:knip`, part of `npm run lint`): unused files,
 * exports, types and dependencies fail the lint. The seeded fixture runs knip
 * in a throwaway package so the real tree is never touched.
 */
import { spawnSync } from "node:child_process";
import {
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

const FRONTEND = join(__dirname, "..", "..");
const KNIP_BIN = join(FRONTEND, "node_modules", ".bin", "knip");

interface PackageJson {
  scripts: Record<string, string>;
}

function packageScripts(): Record<string, string> {
  const pkg = JSON.parse(
    readFileSync(join(FRONTEND, "package.json"), "utf8"),
  ) as PackageJson;
  return pkg.scripts;
}

function seededPackage(dependencies: Record<string, string>): string {
  const dir = mkdtempSync(join(tmpdir(), "knip-gate-"));
  mkdirSync(join(dir, "src"));
  writeFileSync(
    join(dir, "package.json"),
    JSON.stringify({ name: "knip-seed", version: "0.0.0", dependencies }),
  );
  writeFileSync(
    join(dir, "knip.json"),
    JSON.stringify({ entry: ["src/index.ts"], project: ["src/**/*.ts"] }),
  );
  writeFileSync(join(dir, "src", "index.ts"), 'import "./used";\n');
  writeFileSync(join(dir, "src", "used.ts"), "export const used = 1;\n");
  return dir;
}

function runKnip(dir: string): number | null {
  return spawnSync(KNIP_BIN, ["--no-progress"], { cwd: dir, encoding: "utf8" })
    .status;
}

const seeded: string[] = [];

afterEach(() => {
  seeded.splice(0).forEach((dir) => {
    rmSync(dir, { recursive: true, force: true });
  });
});

describe("knip gate", () => {
  it("is part of npm run lint and keeps knip's exit code", () => {
    const scripts = packageScripts();
    expect(scripts.lint).toContain("npm run lint:knip");
    expect(scripts["lint:knip"]).toBe("knip --no-progress");
  });

  it("allows only the documented braces dependency ignore", () => {
    const config = readFileSync(join(FRONTEND, "knip.ts"), "utf8");
    expect(config).toContain('ignoreDependencies: ["braces"]');
  });

  it("fails on a seeded unused dependency", () => {
    const dir = seededPackage({ "left-pad": "1.3.0" });
    seeded.push(dir);
    expect(runKnip(dir)).not.toBe(0);
  });

  it("fails on a seeded unused export", () => {
    const dir = seededPackage({});
    seeded.push(dir);
    writeFileSync(
      join(dir, "src", "used.ts"),
      "export const unusedExport = 1;\n",
    );
    expect(runKnip(dir)).not.toBe(0);
  });

  it("passes on a clean seeded package", () => {
    const dir = seededPackage({});
    seeded.push(dir);
    writeFileSync(join(dir, "src", "index.ts"), "export {};\n");
    rmSync(join(dir, "src", "used.ts"));
    expect(runKnip(dir)).toBe(0);
  });
});
