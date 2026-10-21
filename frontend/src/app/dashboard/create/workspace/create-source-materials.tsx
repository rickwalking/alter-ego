"use client";

import { useTranslations } from "next-intl";
import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";

import { NeonButton } from "@/components/atoms/neon-button";
import {
  NeonCard,
  NeonCardContent,
  NeonCardHeader,
  NeonCardTitle,
} from "@/components/molecules/neon-card";

import type { ContentSource } from "@/modules/publishing";

interface CreateSourceMaterialsProps {
  projectId: string;
  onSourcesChange?: (sources: ContentSource[]) => void;
}

import { AddSourceForm, SourceItem } from "./create-source-parts";
import { useProjectSources, useSourceForm } from "./use-project-sources";

export function CreateSourceMaterials({
  projectId,
  onSourcesChange,
}: Readonly<CreateSourceMaterialsProps>): React.JSX.Element {
  const t = useTranslations("editorialWorkflow");
  const list = useProjectSources(projectId, onSourcesChange);
  const form = useSourceForm(projectId, list);
  const { sources, loading, error } = list;

  return (
    <NeonCard>
      <NeonCardHeader className="flex flex-row items-center justify-between">
        <NeonCardTitle>{t("sourcesTitle")}</NeonCardTitle>
        <NeonButton
          size="sm"
          variant="outline"
          disabled={loading}
          onClick={() => void list.loadSources()}
        >
          {t("actions.refresh")}
        </NeonButton>
      </NeonCardHeader>
      <NeonCardContent className="max-h-[520px] space-y-4 overflow-y-auto">
        <AddSourceForm form={form} />

        {error && (
          <NeonAlert variant="destructive">
            <NeonAlertDescription>{error}</NeonAlertDescription>
          </NeonAlert>
        )}
        {sources.length === 0 && (
          <p className="text-sm text-muted-foreground">{t("noSources")}</p>
        )}
        {sources.map((source) => (
          <SourceItem
            key={source.id}
            source={source}
            onExtract={list.extractKeyPoints}
          />
        ))}
      </NeonCardContent>
    </NeonCard>
  );
}
