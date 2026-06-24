import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { apiCall, apiCallNoContent } from "@/lib/api-client";
import {
  customPaletteSchema,
  type CustomPalette,
  type PaletteCreateRequest,
  type PaletteUpdateRequest,
} from "@/schemas/palette";
import { paletteCatalogOptions, paletteKeys } from "@/modules/palette/queries";

/** Read the palette catalog (roots + active custom). Plain query so the create
 * flow can degrade gracefully if the catalog is briefly unavailable. */
export function usePaletteCatalog() {
  return useQuery(paletteCatalogOptions());
}

export function useCreatePalette() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PaletteCreateRequest) =>
      apiCall<CustomPalette>(API_ENDPOINTS.PALETTES, customPaletteSchema, {
        method: HTTP_METHODS.POST,
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: paletteKeys.catalog() });
    },
  });
}

export function useUpdatePalette() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PaletteUpdateRequest }) =>
      apiCall<CustomPalette>(
        API_ENDPOINTS.PALETTE_BY_ID(id),
        customPaletteSchema,
        { method: HTTP_METHODS.PATCH, body: JSON.stringify(data) },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: paletteKeys.catalog() });
    },
  });
}

export function useArchivePalette() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiCallNoContent(API_ENDPOINTS.PALETTE_BY_ID(id), {
        method: HTTP_METHODS.DELETE,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: paletteKeys.catalog() });
    },
  });
}
