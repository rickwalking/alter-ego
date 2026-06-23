/**
 * Rule-fires regression test for the palette-drift gate (AE-0180 standard).
 *
 * Proves `scripts/check-palette-drift.mjs --strict` EXITS NON-ZERO on a seeded
 * desync between the backend palette contract and the frontend create-form /
 * i18n constants — not merely that the real tree passes. Each case writes
 * fixtures to a temp dir and points the checker at them via its env overrides
 * (PALETTE_CONTRACT_PATH / CREATE_TS_PATH / I18N_EN_PATH / I18N_PT_PATH).
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
    {
      key: "lumen",
      mode: "light",
      kind: "variant",
      label_en: "Lumen",
      label_pt: "Lume",
    },
  ],
  light_theme_keys: ["lumen"],
  image_presets: [{ model: "openai", style: "neo_anime" }],
};

const CREATE_TS_OK = `
export const CAROUSEL_THEMES = {
  ALPHA: "alpha",
  LUMEN: "lumen",
  AUTO: "auto",
} as const;
export const THEME_LABEL_KEYS = {
  alpha: "themes.alpha",
  lumen: "themes.lumen",
  auto: "themes.auto",
} as const;
export const LIGHT_THEME_KEYS: readonly string[] = [CAROUSEL_THEMES.LUMEN];
export const IMAGE_PRESETS = [
  { value: "openai__neo_anime", model: "openai", style: "neo_anime" },
] as const;
`;

const EN_OK = {
  create: { themes: { alpha: "Alpha", lumen: "Lumen", auto: "Auto-detect" } },
};
const PT_OK = {
  create: { themes: { alpha: "Alfa", lumen: "Lume", auto: "Auto-detectar" } },
};

interface Fixture {
  createTs?: string;
  en?: unknown;
  pt?: unknown;
}

let dir: string;

beforeEach(() => {
  dir = mkdtempSync(join(tmpdir(), "palette-drift-"));
});
afterEach(() => {
  rmSync(dir, { recursive: true, force: true });
});

function run({
  createTs = CREATE_TS_OK,
  en = EN_OK,
  pt = PT_OK,
}: Fixture): number {
  const contractPath = join(dir, "palettes.json");
  const createPath = join(dir, "create.ts");
  const enPath = join(dir, "en.json");
  const ptPath = join(dir, "pt.json");
  writeFileSync(contractPath, JSON.stringify(CONTRACT));
  writeFileSync(createPath, createTs);
  writeFileSync(enPath, JSON.stringify(en));
  writeFileSync(ptPath, JSON.stringify(pt));
  try {
    execFileSync("node", [CHECKER, "--strict"], {
      cwd: FRONTEND_ROOT,
      encoding: "utf8",
      stdio: ["pipe", "pipe", "pipe"],
      env: {
        ...process.env,
        PALETTE_CONTRACT_PATH: contractPath,
        CREATE_TS_PATH: createPath,
        I18N_EN_PATH: enPath,
        I18N_PT_PATH: ptPath,
      },
    });
    return 0;
  } catch (err) {
    return (err as { status?: number }).status ?? 1;
  }
}

describe("palette-drift gate fires on seeded drift (AE-0266 Phase 3)", () => {
  it("passes (exit 0) when create.ts + i18n match the contract", () => {
    expect(run({})).toBe(0);
  });

  it("ERRORS when a contract theme is missing from CAROUSEL_THEMES", () => {
    const createTs = CREATE_TS_OK.replace('  LUMEN: "lumen",\n', "");
    expect(run({ createTs })).not.toBe(0);
  });

  it("ERRORS when an i18n (en) label diverges from the contract", () => {
    const en = {
      create: {
        themes: { alpha: "WRONG", lumen: "Lumen", auto: "Auto-detect" },
      },
    };
    expect(run({ en })).not.toBe(0);
  });

  it("ERRORS when a pt label is missing", () => {
    const pt = { create: { themes: { alpha: "Alfa", auto: "Auto-detectar" } } };
    expect(run({ pt })).not.toBe(0);
  });

  it("ERRORS when an IMAGE_PRESETS combo is missing", () => {
    const createTs = CREATE_TS_OK.replace(
      '  { value: "openai__neo_anime", model: "openai", style: "neo_anime" },\n',
      "",
    );
    expect(run({ createTs })).not.toBe(0);
  });

  it("ERRORS when LIGHT_THEME_KEYS omits a light theme", () => {
    const createTs = CREATE_TS_OK.replace(
      "export const LIGHT_THEME_KEYS: readonly string[] = [CAROUSEL_THEMES.LUMEN];",
      "export const LIGHT_THEME_KEYS: readonly string[] = [];",
    );
    expect(run({ createTs })).not.toBe(0);
  });
});
