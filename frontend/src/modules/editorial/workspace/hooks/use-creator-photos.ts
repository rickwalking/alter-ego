import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { apiCall, apiUpload } from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";

/** AE-0376: one photo of the owner's library. */
export const creatorPhotoSchema = z.object({
  id: z.string(),
  role: z.string().nullable().optional(),
  pose_tag: z.string().nullable().optional(),
  created_at: z.string(),
});
const creatorPhotoListSchema = z.object({ items: z.array(creatorPhotoSchema) });
const hookPhotoResponseSchema = z.object({
  project_id: z.string(),
  hook_asset_id: z.string(),
});

export type CreatorPhoto = z.infer<typeof creatorPhotoSchema>;

export const creatorPhotoKeys = {
  list: (role: string) => ["creator-photos", role] as const,
};

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

export interface UploadCreatorPhotoInput {
  file: File;
  role: string;
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

export interface SetHookPhotoInput {
  projectId: string;
  assetId: string;
}

/** Use one of the owner's photos on slide 1 of a POV carousel. */
export function useSetHookPhoto() {
  return useMutation({
    mutationFn: async ({ projectId, assetId }: SetHookPhotoInput) =>
      apiCall(
        API_ENDPOINTS.CAROUSEL_HOOK_PHOTO(projectId),
        hookPhotoResponseSchema,
        {
          method: HTTP_METHODS.PUT,
          body: JSON.stringify({ creator_asset_id: assetId }),
        },
      ),
  });
}
