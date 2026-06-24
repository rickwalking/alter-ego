import type { PaletteMode } from "@/schemas/palette";

/**
 * The image style is DERIVED from the palette mode, never user-chosen (D3): a
 * light palette can therefore never be paired with a dark scene. These keys map
 * to i18n labels under the "palettes" namespace (`derivedStyle.*`).
 */
const MODE_STYLE_LABEL_KEY: Record<PaletteMode, string> = {
  light: "derivedStyle.light",
  dark: "derivedStyle.dark",
};

/** The i18n key for the read-only derived image style of a mode. */
export function derivedImageStyleKey(mode: PaletteMode): string {
  return MODE_STYLE_LABEL_KEY[mode];
}
