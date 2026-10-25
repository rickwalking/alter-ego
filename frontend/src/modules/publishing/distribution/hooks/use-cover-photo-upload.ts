import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { HTTP_STATUS } from "@/constants/api";
import { ApiError } from "@/lib/api-client";
import { coverOptionKeys } from "./use-cover-picker";
import { UPLOAD_FAILURE } from "@/modules/publishing/distribution/constants";
import type {
  CoverPhotoUpload,
  CoverPhotoUploadDeps,
  UploadFailure,
} from "./types";

const SERVER_ERROR_MIN = 500;

/**
 * The cause of a failed upload. ``fetch`` rejects with a ``TypeError`` when no
 * HTTP answer arrives (the network); any other unexpected error reads as the
 * server's.
 */
export function uploadFailure(err: unknown): UploadFailure {
  if (err instanceof TypeError) {
    return UPLOAD_FAILURE.NETWORK;
  }
  if (!(err instanceof ApiError) || err.status >= SERVER_ERROR_MIN) {
    return UPLOAD_FAILURE.SERVER;
  }
  return err.status === HTTP_STATUS.TOO_MANY_REQUESTS
    ? UPLOAD_FAILURE.RATE_LIMITED
    : UPLOAD_FAILURE.INVALID;
}

/**
 * "Enviar foto" in the cover generation panel. The page's library upload
 * stores the file (same endpoint and limits as the wizard); then the cover
 * options refresh, and once they list the photo ``onListed`` ticks it, so an
 * unlisted photo never counts toward the three.
 */
export function useCoverPhotoUpload({
  projectId,
  upload,
  listedIds,
  onListed,
}: CoverPhotoUploadDeps): CoverPhotoUpload {
  const queryClient = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [failure, setFailure] = useState<UploadFailure | null>(null);
  const [waiting, setWaiting] = useState<readonly string[]>([]);
  const listed = waiting.filter((assetId) => listedIds.includes(assetId));
  if (listed.length > 0) {
    setWaiting(waiting.filter((assetId) => !listed.includes(assetId)));
    listed.forEach(onListed);
  }
  const onFile = useCallback(
    async (file: File): Promise<void> => {
      if (!upload) {
        return;
      }
      setUploading(true);
      setFailure(null);
      try {
        const assetId = await upload(file);
        setWaiting((current) => [...current, assetId]);
      } catch (err) {
        setFailure(uploadFailure(err));
        return;
      } finally {
        setUploading(false);
      }
      void queryClient.invalidateQueries({
        queryKey: coverOptionKeys.detail(projectId),
      });
    },
    [upload, queryClient, projectId],
  );
  return { available: upload !== undefined, uploading, failure, onFile };
}
