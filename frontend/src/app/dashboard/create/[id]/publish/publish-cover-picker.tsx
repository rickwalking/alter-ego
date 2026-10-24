"use client";

import { useCallback, useMemo } from "react";
import { useLocale } from "next-intl";
import { findThemePalette } from "@/app/dashboard/create/theme-options";
import { CoverPromptSuggestions } from "@/modules/editorial";
import { usePaletteCatalog } from "@/modules/palette";
import { CoverPickerSection } from "@/modules/publishing";
import type { PublishCoverPickerProps } from "./types";

/**
 * The publish step's cover picker with the create wizard's prompt
 * suggestions under its "Gerar capa com Grok" prompt, tailored to the
 * carousel's topic and palette. Tapping one fills the prompt, which stays
 * editable.
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
          palette={palette}
          onPick={fill}
        />
      );
    },
    [project.topic, palette],
  );
  return (
    <CoverPickerSection
      projectId={projectId}
      onSwitched={onSwitched}
      renderPromptSuggestions={renderSuggestions}
    />
  );
}
