/**
 * `palette` — bounded-context public contract (AE-0271).
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
  usePaletteCatalog,
  useUpdatePalette,
} from "@/modules/palette/hooks/use-palettes";
export { paletteCatalogOptions, paletteKeys } from "@/modules/palette/queries";
