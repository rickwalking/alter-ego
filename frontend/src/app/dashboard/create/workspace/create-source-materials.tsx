"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonButton } from "@/components/atoms/neon-button";
import {
  NeonCard,
  NeonCardContent,
  NeonCardHeader,
  NeonCardTitle,
} from "@/components/molecules/neon-card";
import { CONTENT_SOURCE_TYPES } from "@/constants/blog-ai";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import type { ContentSource } from "@/features/blog/types-ai";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

interface CreateSourceMaterialsProps {
  projectId: string;
  onSourcesChange?: (sources: ContentSource[]) => void;
}

const SOURCE_TYPE_OPTIONS = [
  CONTENT_SOURCE_TYPES.URL,
  CONTENT_SOURCE_TYPES.DOCUMENT,
  CONTENT_SOURCE_TYPES.NOTE,
  CONTENT_SOURCE_TYPES.INTERVIEW,
  CONTENT_SOURCE_TYPES.DATA,
] as const;

export function CreateSourceMaterials({
  projectId,
  onSourcesChange,
}: CreateSourceMaterialsProps): React.JSX.Element {
  const t = useTranslations("editorialWorkflow");
  const [sources, setSources] = useState<ContentSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [sourceType, setSourceType] = useState<string>(
    CONTENT_SOURCE_TYPES.NOTE,
  );

  const updateSources = useCallback(
    (next: ContentSource[]) => {
      setSources(next);
      onSourcesChange?.(next);
    },
    [onSourcesChange],
  );

  const loadSources = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await authenticatedFetch(
        API_ENDPOINTS.PROJECT_SOURCES(projectId),
      );
      if (!response.ok) {
        throw new Error("Failed to load sources");
      }
      const payload = (await response.json()) as { items: ContentSource[] };
      updateSources(payload.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sources");
    } finally {
      setLoading(false);
    }
  }, [projectId, updateSources]);

  const addSource = async (
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> => {
    event.preventDefault();
    if (!title.trim() || !content.trim()) {
      return;
    }

    setAdding(true);
    setError(null);
    try {
      const response = await authenticatedFetch(
        API_ENDPOINTS.PROJECT_SOURCES(projectId),
        {
          method: HTTP_METHODS.POST,
          body: JSON.stringify({
            title: title.trim(),
            content: content.trim(),
            source_type: sourceType,
          }),
        },
      );
      if (!response.ok) {
        throw new Error("Failed to add source");
      }
      const created = (await response.json()) as ContentSource;
      updateSources([created, ...sources]);
      setTitle("");
      setContent("");
      setSourceType(CONTENT_SOURCE_TYPES.NOTE);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add source");
    } finally {
      setAdding(false);
    }
  };

  const extractKeyPoints = async (sourceId: string): Promise<void> => {
    const response = await authenticatedFetch(
      API_ENDPOINTS.PROJECT_SOURCE_EXTRACT(projectId, sourceId),
      { method: HTTP_METHODS.POST },
    );
    if (!response.ok) {
      throw new Error("Extraction failed");
    }
    const updated = (await response.json()) as ContentSource;
    updateSources(
      sources.map((source) => (source.id === sourceId ? updated : source)),
    );
  };

  useEffect(() => {
    void loadSources();
  }, [loadSources]);

  return (
    <NeonCard>
      <NeonCardHeader className="flex flex-row items-center justify-between">
        <NeonCardTitle>{t("sourcesTitle")}</NeonCardTitle>
        <NeonButton
          size="sm"
          variant="outline"
          disabled={loading}
          onClick={() => void loadSources()}
        >
          {t("actions.refresh")}
        </NeonButton>
      </NeonCardHeader>
      <NeonCardContent className="max-h-[520px] space-y-4 overflow-y-auto">
        <form
          className="shrink-0 space-y-3 rounded-md border p-3"
          onSubmit={(event) => void addSource(event)}
        >
          <p className="font-medium text-sm">{t("addSourceTitle")}</p>
          <div className="space-y-2">
            <label htmlFor="source-title" className="block text-sm">
              {t("fields.title")}
            </label>
            <input
              id="source-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-background)] px-3 py-2 text-sm text-[var(--color-text)]"
              placeholder={t("fields.titlePlaceholder")}
              required
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="source-type" className="block text-sm">
              {t("fields.type")}
            </label>
            <select
              id="source-type"
              value={sourceType}
              onChange={(event) => setSourceType(event.target.value)}
              className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-background)] px-3 py-2 text-sm text-[var(--color-text)] [&>option]:bg-[var(--color-background)] [&>option]:text-[var(--color-text)]"
            >
              {SOURCE_TYPE_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {t(`sourceTypes.${option}`)}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <label htmlFor="source-content" className="block text-sm">
              {t("fields.content")}
            </label>
            <textarea
              id="source-content"
              value={content}
              onChange={(event) => setContent(event.target.value)}
              rows={4}
              className="w-full resize-none overflow-y-auto rounded-md border border-[var(--color-border)] bg-[var(--color-background)] px-3 py-2 text-sm text-[var(--color-text)]"
              style={{ maxHeight: "120px" }}
              placeholder={t("fields.contentPlaceholder")}
              required
            />
          </div>
          <NeonButton type="submit" size="sm" disabled={adding}>
            {adding ? t("actions.adding") : t("actions.addSource")}
          </NeonButton>
        </form>

        {error && (
          <NeonAlert variant="destructive">
            <NeonAlertDescription>{error}</NeonAlertDescription>
          </NeonAlert>
        )}
        {sources.length === 0 && (
          <p className="text-sm text-muted-foreground">{t("noSources")}</p>
        )}
        {sources.map((source) => (
          <div key={source.id} className="rounded-md border p-3 space-y-2">
            <div className="flex items-center justify-between">
              <p className="font-medium">{source.title}</p>
              <NeonBadge variant="outline">{source.source_type}</NeonBadge>
            </div>
            <p className="text-sm text-muted-foreground line-clamp-3">
              {source.content}
            </p>
            {source.extracted_key_points.length > 0 && (
              <ul className="text-sm list-disc pl-5">
                {source.extracted_key_points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            )}
            <NeonButton
              size="sm"
              onClick={() => void extractKeyPoints(source.id)}
            >
              {t("actions.extract")}
            </NeonButton>
          </div>
        ))}
      </NeonCardContent>
    </NeonCard>
  );
}
