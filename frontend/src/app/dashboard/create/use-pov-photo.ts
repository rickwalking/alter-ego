import { useCallback, useEffect, useMemo, useRef } from "react";
import { CREATOR_PHOTO_ROLES } from "@/constants/create";
import {
  useCreatorPhotos,
  useSetHookPhoto,
  useUploadCreatorPhoto,
} from "@/modules/editorial";
import type { CreatePhotoSectionProps } from "@/app/dashboard/create/workspace/create-photo-section";

export interface PovPhotoState {
  section: CreatePhotoSectionProps;
  /** Bind the chosen photo to a just-created project (no-op without one). */
  attachTo: (projectId: string) => Promise<void>;
}

/**
 * AE-0376: the wizard's "Foto do slide 1": the owner's hook photos (newest
 * first, preselected once), upload, and binding after the project is created.
 */
export function usePovPhoto(
  selectedId: string,
  onSelect: (id: string) => void,
): PovPhotoState {
  const role = CREATOR_PHOTO_ROLES.HOOK;
  const photos = useCreatorPhotos(role);
  const upload = useUploadCreatorPhoto();
  const setHookPhoto = useSetHookPhoto();
  const preselected = useRef(false);
  const items = useMemo(() => photos.data ?? [], [photos.data]);

  useEffect(() => {
    if (preselected.current || items.length === 0) {
      return;
    }
    preselected.current = true;
    if (!selectedId) {
      onSelect(items[0].id);
    }
  }, [items, selectedId, onSelect]);

  const onUpload = useCallback(
    (file: File) =>
      upload.mutate(
        { file, role },
        { onSuccess: (photo) => onSelect(photo.id) },
      ),
    [upload, role, onSelect],
  );

  const attachTo = useCallback(
    async (projectId: string): Promise<void> => {
      if (!selectedId) {
        return;
      }
      await setHookPhoto.mutateAsync({ projectId, assetId: selectedId });
    },
    [selectedId, setHookPhoto],
  );

  return {
    section: {
      photos: items,
      selectedId,
      onSelect,
      onUpload,
      uploading: upload.isPending,
      uploadFailed: upload.isError,
    },
    attachTo,
  };
}
