import type { PaletteCatalogResponse, PaletteMode } from "@/schemas/palette";

/** The FE-only "let the backend auto-detect" theme value. */
export const AUTO_THEME_VALUE = "auto";

const LOCALE_PT = "pt";

/** A theme dropdown entry built from the dynamic catalog (AE-0271). */
export interface ThemeOption {
  /** root key | "auto" | custom-palette UUID — the value stored on the project. */
  readonly value: string;
  readonly label: string;
  /** Light/dark, or null for the auto sentinel (no preset nudge). */
  readonly mode: PaletteMode | null;
}

/**
 * Build the theme dropdown options: the auto sentinel, then read-only roots
 * (localised label), then active custom palettes (user name). Returns just the
 * auto option when the catalog is unavailable, so the create flow never breaks.
 */
export function buildThemeOptions(
  catalog: PaletteCatalogResponse | undefined,
  locale: string,
  autoLabel: string,
): ThemeOption[] {
  const options: ThemeOption[] = [
    { value: AUTO_THEME_VALUE, label: autoLabel, mode: null },
  ];
  if (!catalog) return options;
  for (const root of catalog.roots) {
    options.push({
      value: root.key,
      label: locale === LOCALE_PT ? root.label_pt : root.label_en,
      mode: root.mode,
    });
  }
  for (const palette of catalog.custom) {
    options.push({
      value: palette.id,
      label: palette.name,
      mode: palette.mode,
    });
  }
  return options;
}

/** The mode of the option with this value, or null if unknown / auto. */
export function findThemeMode(
  options: readonly ThemeOption[],
  value: string,
): PaletteMode | null {
  return options.find((option) => option.value === value)?.mode ?? null;
}
