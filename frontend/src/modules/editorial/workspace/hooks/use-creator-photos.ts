import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import {
  ApiError,
  apiCall,
  apiCallNoContent,
  apiUpload,
} from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS, HTTP_STATUS } from "@/constants/api";
import type { UploadCreatorPhotoInput } from "./types";

/** One photo of the owner's library. */
export const creatorPhotoSchema = z.object({
  id: z.string(),
  role: z.string().nullable().optional(),
  pose_tag: z.string().nullable().optional(),
  created_at: z.string(),
});
const creatorPhotoListSchema = z.object({ items: z.array(creatorPhotoSchema) });

export type CreatorPhoto = z.infer<typeof creatorPhotoSchema>;

/** The 409 `detail` of deleting a photo a carousel still uses. */
const photoInUseSchema = z.object({
  code: z.string(),
  carousels: z.array(
    z.object({ id: z.string(), title: z.string().nullable() }),
  ),
});

export type PhotoInUseCarousel = z.infer<
  typeof photoInUseSchema
>["carousels"][number];

export const creatorPhotoKeys = {
  all: ["creator-photos"] as const,
  list: (role: string) => ["creator-photos", role] as const,
};

/** The carousels that block a delete, or null when `error` is not that 409. */
export function photoInUseCarousels(
  error: unknown,
): PhotoInUseCarousel[] | null {
  if (!(error instanceof ApiError) || error.status !== HTTP_STATUS.CONFLICT) {
    return null;
  }
  const parsed = photoInUseSchema.safeParse(error.detail);
  return parsed.success ? parsed.data.carousels : null;
}

/** The owner's photos for a role, newest first (the first is the last used). */
export function useCreatorPhotos(role: string) {
  return useQuery({
    queryKey: creatorPhotoKeys.list(role),
    queryFn: async (): Promise<CreatorPhoto[]> => {
      const url = `${API_ENDPOINTS.CREATOR_ASSETS}?role=${encodeURIComponent(role)}`;
      const data = await apiCall(url, creatorPhotoListSchema);
      return data.items;
    },
  });
}

/** Upload a photo (PNG/WebP keep transparency, ≤5 MB) to the library. */
export function useUploadCreatorPhoto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      file,
      role,
    }: UploadCreatorPhotoInput): Promise<CreatorPhoto> => {
      const form = new FormData();
      form.append("file", file);
      form.append("role", role);
      return apiUpload(API_ENDPOINTS.CREATOR_ASSETS, creatorPhotoSchema, form);
    },
    onSuccess: (_photo, { role }) => {
      void queryClient.invalidateQueries({
        queryKey: creatorPhotoKeys.list(role),
      });
    },
  });
}

/** Delete one of the owner's photos (409 while a carousel uses it). */
export function useDeleteCreatorPhoto() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (photoId: string) =>
      apiCallNoContent(API_ENDPOINTS.CREATOR_ASSET_BY_ID(photoId), {
        method: HTTP_METHODS.DELETE,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: creatorPhotoKeys.all });
    },
  });
}
