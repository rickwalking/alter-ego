import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { coverOptionKeys } from "./use-cover-picker";
import type { CoverPhotoUpload, UploadLibraryPhoto } from "./types";

/**
 * "Enviar foto" in the cover generation panel. The page's library upload
 * stores the file (same endpoint and limits as the wizard); then the cover
 * options refresh so the photo shows up and ``onUploaded`` ticks it.
 */
export function useCoverPhotoUpload(
  projectId: string,
  upload: UploadLibraryPhoto | undefined,
  onUploaded: (assetId: string) => void,
): CoverPhotoUpload {
  const queryClient = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [failed, setFailed] = useState(false);
  const onFile = useCallback(
    async (file: File): Promise<void> => {
      if (!upload) {
        return;
      }
      setUploading(true);
      setFailed(false);
      try {
        onUploaded(await upload(file));
        await queryClient.invalidateQueries({
          queryKey: coverOptionKeys.detail(projectId),
        });
      } catch {
        setFailed(true);
      } finally {
        setUploading(false);
      }
    },
    [upload, onUploaded, queryClient, projectId],
  );
  return { available: upload !== undefined, uploading, failed, onFile };
}
