import { queryOptions } from "@tanstack/react-query";
import { API_ENDPOINTS } from "@/constants/api";
import { apiCall } from "@/lib/api-client";
import {
  paletteCatalogResponseSchema,
  type PaletteCatalogResponse,
} from "@/schemas/palette";

export const paletteKeys = {
  catalog: () => ["palette-catalog"] as const,
};

export function paletteCatalogOptions() {
  return queryOptions({
    queryKey: paletteKeys.catalog(),
    queryFn: () =>
      apiCall<PaletteCatalogResponse>(
        API_ENDPOINTS.PALETTES,
        paletteCatalogResponseSchema,
      ),
  });
}
