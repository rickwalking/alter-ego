import { useCallback, useEffect, useMemo, useRef } from "react";
import { CREATOR_PHOTO_ROLES } from "@/constants/create";
import {
  photoInUseCarousels,
  useCreatorPhotos,
  useDeleteCreatorPhoto,
  useUploadCreatorPhoto,
} from "@/modules/editorial";
import type { CreatePhotoSectionProps } from "@/app/dashboard/create/workspace/create-photo-section";

export interface PovPhotoState {
  section: CreatePhotoSectionProps;
}

interface PhotoDeleteDeps {
  selectedId: string;
  items: readonly { id: string }[];
  onSelect: (id: string) => void;
}

type PhotoDeleteFields = Pick<
  CreatePhotoSectionProps,
  "onDelete" | "deleting" | "deleteBlockedBy" | "deleteFailed"
>;

/** Delete a library photo; deleting the selected one selects the newest left. */
function usePhotoDelete({
  selectedId,
  items,
  onSelect,
}: Readonly<PhotoDeleteDeps>): PhotoDeleteFields {
  const remove = useDeleteCreatorPhoto();
  const onDelete = useCallback(
    (photoId: string) =>
      remove.mutate(photoId, {
        onSuccess: () => {
          if (photoId !== selectedId) return;
          const next = items.find((photo) => photo.id !== photoId);
          onSelect(next?.id ?? "");
        },
      }),
    [remove, selectedId, items, onSelect],
  );

  return {
    onDelete,
    deleting: remove.isPending,
    deleteBlockedBy: photoInUseCarousels(remove.error),
    deleteFailed: remove.isError,
  };
}

/**
 * The wizard's "Foto do slide 1": the owner's hook photos (newest
 * first, preselected once) and upload. PR #106 review: the chosen photo is
 * sent as `hook_asset_id` in the create request (required for POV), so the
 * backend binds it before the project exists without its photo. Deleting the
 * selected photo selects the newest remaining one; a 409 carries the carousels
 * that still use the photo.
 */
export function usePovPhoto(
  selectedId: string,
  onSelect: (id: string) => void,
): PovPhotoState {
  const role = CREATOR_PHOTO_ROLES.HOOK;
  const photos = useCreatorPhotos(role);
  const upload = useUploadCreatorPhoto();
  const preselected = useRef(false);
  const items = useMemo(() => photos.data ?? [], [photos.data]);

  useEffect(() => {
    const first = items[0];
    if (preselected.current || first === undefined) {
      return;
    }
    preselected.current = true;
    if (!selectedId) {
      onSelect(first.id);
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

  const deletion = usePhotoDelete({ selectedId, items, onSelect });

  return {
    section: {
      photos: items,
      selectedId,
      onSelect,
      onUpload,
      uploading: upload.isPending,
      uploadFailed: upload.isError,
      ...deletion,
    },
  };
}
