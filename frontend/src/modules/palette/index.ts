/**
 * `palette` — bounded-context public contract.
 *
 * Owns the custom-palette catalog surface consumed by `app/`: the TanStack
 * Query hooks over `GET/POST/PATCH/DELETE /api/palettes`. This barrel is the
 * ONLY import surface for `app/` and cross-context consumers; everything else
 * under `modules/palette/**` is internal.
 *
 * See `src/modules/README.md` for the public-contract convention.
 */

export {
  useArchivePalette,
  useCreatePalette,
  useGeneratePalettes,
  usePaletteCatalog,
  useUpdatePalette,
} from "@/modules/palette/hooks/use-palettes";
export { paletteCatalogOptions, paletteKeys } from "@/modules/palette/queries";
