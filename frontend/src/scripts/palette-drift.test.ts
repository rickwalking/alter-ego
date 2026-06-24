/**
 * Rule-fires regression test for the palette-drift gate (AE-0180 standard).
 *
 * Proves `scripts/check-palette-drift.mjs --strict` EXITS NON-ZERO on a seeded
 * desync between the backend palette contract and the frontend `IMAGE_PRESETS`
 * — not merely that the real tree passes. Each case writes fixtures to a temp
 * dir and points the checker at them via its env overrides
 * (PALETTE_CONTRACT_PATH / CREATE_TS_PATH).
 *
 * Retargeted by AE-0271: the theme list is now rendered dynamically from
 * `GET /api/palettes`, so the gate only guards the still-static IMAGE_PRESETS
 * surface. The theme-key / label / light-key / i18n drift cases were removed
 * with the FE constants they checked.
 *
 * Gherkin: tests/features/palette-drift-gate.feature
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

const FRONTEND_ROOT = join(import.meta.dirname, "..", "..");
const CHECKER = join(FRONTEND_ROOT, "scripts", "check-palette-drift.mjs");

const CONTRACT = {
  themes: [
    {
      key: "alpha",
      mode: "dark",
      kind: "category",
      label_en: "Alpha",
      label_pt: "Alfa",
    },
  ],
  light_theme_keys: [],
  image_presets: [
    { model: "openai", style: "neo_anime" },
    { model: "gemini", style: "comic_neon" },
  ],
};

const CREATE_TS_OK = `
export const IMAGE_PRESETS = [
  { value: "openai__neo_anime", model: "openai", style: "neo_anime" },
  { value: "gemini__comic_neon", model: "gemini", style: "comic_neon" },
] as const;
`;

interface Fixture {
  createTs?: string;
}

let dir: string;

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "palette-drift-"));
});
afterEach(() => {
  rmSync(dir, { recursive: true, force: true });
});

function run({ createTs = CREATE_TS_OK }: Fixture): number {
  const contractPath = join(dir, "palettes.json");
  const createPath = join(dir, "create.ts");
  writeFileSync(contractPath, JSON.stringify(CONTRACT));
  writeFileSync(createPath, createTs);
  try {
    execFileSync("node", [CHECKER, "--strict"], {
      cwd: FRONTEND_ROOT,
      encoding: "utf8",
      stdio: ["pipe", "pipe", "pipe"],
      env: {
        ...process.env,
        PALETTE_CONTRACT_PATH: contractPath,
        CREATE_TS_PATH: createPath,
      },
    });
    return 0;
  } catch (err) {
    return (err as { status?: number }).status ?? 1;
  }
}

describe("palette-drift gate fires on seeded IMAGE_PRESETS drift (AE-0271)", () => {
  it("passes (exit 0) when IMAGE_PRESETS match the contract", () => {
    expect(run({})).toBe(0);
  });

  it("ERRORS when an IMAGE_PRESETS combo is missing", () => {
    const createTs = CREATE_TS_OK.replace(
      '  { value: "gemini__comic_neon", model: "gemini", style: "comic_neon" },\n',
      "",
    );
    expect(run({ createTs })).not.toBe(0);
  });

  it("ERRORS when an unexpected IMAGE_PRESETS combo is present", () => {
    const createTs = CREATE_TS_OK.replace(
      "] as const;",
      '  { value: "openai__rogue_style", model: "openai", style: "rogue_style" },\n] as const;',
    );
    expect(run({ createTs })).not.toBe(0);
  });
});
