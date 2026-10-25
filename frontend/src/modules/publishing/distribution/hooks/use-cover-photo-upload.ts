import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { HTTP_STATUS } from "@/constants/api";
import { ApiError } from "@/lib/api-client";
import { coverOptionKeys } from "./use-cover-picker";
import type {
  CoverPhotoUpload,
  CoverPhotoUploadDeps,
  UploadFailure,
} from "./types";

const SERVER_ERROR_MIN = 500;

/** The cause of a failed upload: no HTTP answer is the network. */
export function uploadFailure(err: unknown): UploadFailure {
  if (!(err instanceof ApiError)) {
    return "network";
  }
  if (err.status === HTTP_STATUS.TOO_MANY_REQUESTS) {
    return "rateLimited";
  }
  return err.status >= SERVER_ERROR_MIN ? "server" : "invalid";
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
  const [waiting, setWaiting] = useState<string | null>(null);
  if (waiting !== null && listedIds.includes(waiting)) {
    setWaiting(null);
    onListed(waiting);
  }
  const onFile = useCallback(
    async (file: File): Promise<void> => {
      if (!upload) {
        return;
      }
      setUploading(true);
      setFailure(null);
      try {
        setWaiting(await upload(file));
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
