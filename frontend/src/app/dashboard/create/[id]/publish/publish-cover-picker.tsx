"use client";

import { useCallback, useMemo } from "react";
import { useLocale } from "next-intl";
import { findThemePalette } from "@/app/dashboard/create/theme-options";
import { CREATOR_PHOTO_ROLES } from "@/constants/create";
import {
  CoverPromptSuggestions,
  useUploadCreatorPhoto,
} from "@/modules/editorial";
import { usePaletteCatalog } from "@/modules/palette";
import { CoverPickerSection } from "@/modules/publishing";
import type { PublishCoverPickerProps } from "./types";

/**
 * The publish step's cover picker with the create wizard's prompt
 * suggestions under its "Gerar capa com Grok" prompt, tailored to the
 * carousel's topic and palette. Tapping one fills the prompt, which stays
 * editable. "Enviar foto" there goes through the wizard's library upload
 * (role ``hook``), so the photo also joins the owner's photo library.
 */
export function PublishCoverPicker({
  projectId,
  project,
  onSwitched,
}: Readonly<PublishCoverPickerProps>): React.ReactElement {
  const locale = useLocale();
  const { data: catalog } = usePaletteCatalog();
  const palette = useMemo(
    () => findThemePalette(catalog, project.theme, locale),
    [catalog, project.theme, locale],
  );
  const renderSuggestions = useCallback(
    function renderSuggestions(
      fill: (prompt: string) => void,
    ): React.ReactNode {
      return (
        <CoverPromptSuggestions
          topic={project.topic}
          seed={projectId}
          palette={palette}
          onPick={fill}
        />
      );
    },
    [project.topic, palette, projectId],
  );
  const { mutateAsync: uploadToLibrary } = useUploadCreatorPhoto();
  const uploadPhoto = useCallback(
    async (file: File): Promise<string> => {
      const photo = await uploadToLibrary({
        file,
        role: CREATOR_PHOTO_ROLES.HOOK,
      });
      return photo.id;
    },
    [uploadToLibrary],
  );
  return (
    <CoverPickerSection
      projectId={projectId}
      onSwitched={onSwitched}
      renderPromptSuggestions={renderSuggestions}
      uploadPhoto={uploadPhoto}
    />
  );
}
