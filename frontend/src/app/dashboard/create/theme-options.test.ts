import { describe, expect, it } from "vitest";
import type { PaletteCatalogResponse } from "@/schemas/palette";
import {
  AUTO_THEME_VALUE,
  buildThemeOptions,
  findThemeMode,
} from "./theme-options";

// Gherkin: tests/features/palette-drift-gate.feature (the dropdown renders the
// dynamic catalog union; AE-0271).
const CATALOG: PaletteCatalogResponse = {
  roots: [
    {
      key: "plasma_magenta",
      label_en: "Plasma Magenta",
      label_pt: "Magenta Plasma",
      mode: "dark",
      primary: "#ff00ff",
      accent: "#00ffff",
      background: "#0a0a0a",
    },
    {
      key: "clinical_mint",
      label_en: "Clinical Mint",
      label_pt: "Menta Clínica",
      mode: "light",
      primary: "#0a6",
      accent: "#088",
      background: "#fff",
    },
  ],
  custom: [
    {
      id: "11111111-1111-1111-1111-111111111111",
      name: "Aurora",
      slug: "aurora-1111",
      primary: "#102030",
      accent: "#405060",
      background: "#708090",
      mode: "dark",
      keywords: ["space"],
      archived: false,
      created_by: "u1",
      created_at: "2026-06-24T00:00:00Z",
      updated_at: "2026-06-24T00:00:00Z",
    },
  ],
};

describe("buildThemeOptions", () => {
  it("always leads with the auto sentinel", () => {
    const options = buildThemeOptions(undefined, "en", "Auto-detect");
    expect(options).toEqual([
      { value: AUTO_THEME_VALUE, label: "Auto-detect", mode: null },
    ]);
  });

  it("unions auto + roots + custom palettes", () => {
    const options = buildThemeOptions(CATALOG, "en", "Auto");
    expect(options.map((o) => o.value)).toEqual([
      "auto",
      "plasma_magenta",
      "clinical_mint",
      "11111111-1111-1111-1111-111111111111",
    ]);
  });

  it("localises root labels to pt", () => {
    const options = buildThemeOptions(CATALOG, "pt", "Auto");
    expect(options.find((o) => o.value === "plasma_magenta")?.label).toBe(
      "Magenta Plasma",
    );
  });

  it("uses the custom palette name as its label", () => {
    const options = buildThemeOptions(CATALOG, "en", "Auto");
    const custom = options.find((o) => o.value.startsWith("11111111"));
    expect(custom?.label).toBe("Aurora");
  });
});

describe("findThemeMode", () => {
  it("returns the mode of a known option", () => {
    const options = buildThemeOptions(CATALOG, "en", "Auto");
    expect(findThemeMode(options, "clinical_mint")).toBe("light");
    expect(findThemeMode(options, "plasma_magenta")).toBe("dark");
  });

  it("returns null for the auto sentinel and unknowns", () => {
    const options = buildThemeOptions(CATALOG, "en", "Auto");
    expect(findThemeMode(options, "auto")).toBeNull();
    expect(findThemeMode(options, "nope")).toBeNull();
  });
});
