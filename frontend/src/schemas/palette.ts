import { z } from "zod";

/** Strict `#rrggbb` — mirrors the backend allow-list (AE-0270 prompt-injection guard). */
export const HEX_COLOUR_REGEX = /^#[0-9a-fA-F]{6}$/;

/** Light vs dark background — drives the derived image style (read-only, D3). */
export const PALETTE_MODES = ["light", "dark"] as const;
export const paletteModeSchema = z.enum(PALETTE_MODES);

const hexColour = z
  .string()
  .regex(HEX_COLOUR_REGEX, "Use a #rrggbb hex colour");

/** A curated root palette (read-only) projected from the backend registry. */
export const rootPaletteSchema = z.object({
  key: z.string(),
  label_en: z.string(),
  label_pt: z.string(),
  mode: paletteModeSchema,
  primary: z.string(),
  accent: z.string(),
  background: z.string(),
});

/** A user-created custom palette row. */
export const customPaletteSchema = z.object({
  id: z.string(),
  name: z.string(),
  slug: z.string(),
  primary: z.string(),
  accent: z.string(),
  background: z.string(),
  mode: paletteModeSchema,
  keywords: z.array(z.string()),
  archived: z.boolean(),
  created_by: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

/** The full catalog: read-only roots + active custom palettes (AE-0270 GET /palettes). */
export const paletteCatalogResponseSchema = z.object({
  roots: z.array(rootPaletteSchema),
  custom: z.array(customPaletteSchema),
});

/** Create payload — slug + image style are server-derived, never sent (D3/D8). */
export const paletteCreateRequestSchema = z.object({
  name: z.string().min(1).max(80),
  primary: hexColour,
  accent: hexColour,
  background: hexColour,
  mode: paletteModeSchema,
  keywords: z.array(z.string()),
});

/** Patch payload — every field optional; slug stays immutable. */
export const paletteUpdateRequestSchema = z.object({
  name: z.string().min(1).max(80).optional(),
  primary: hexColour.optional(),
  accent: hexColour.optional(),
  background: hexColour.optional(),
  mode: paletteModeSchema.optional(),
  keywords: z.array(z.string()).optional(),
});

export type PaletteMode = z.infer<typeof paletteModeSchema>;
export type RootPalette = z.infer<typeof rootPaletteSchema>;
export type CustomPalette = z.infer<typeof customPaletteSchema>;
export type PaletteCatalogResponse = z.infer<
  typeof paletteCatalogResponseSchema
>;
export type PaletteCreateRequest = z.infer<typeof paletteCreateRequestSchema>;
export type PaletteUpdateRequest = z.infer<typeof paletteUpdateRequestSchema>;
