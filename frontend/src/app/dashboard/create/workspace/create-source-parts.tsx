"use client";

import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonButton } from "@/components/atoms/neon-button";
import { CONTENT_SOURCE_TYPES } from "@/constants/blog-ai";
import type { ContentSource } from "@/modules/publishing";
import type { SourceForm } from "./use-project-sources";

const SOURCE_TYPE_OPTIONS = [
  CONTENT_SOURCE_TYPES.URL,
  CONTENT_SOURCE_TYPES.DOCUMENT,
  CONTENT_SOURCE_TYPES.NOTE,
  CONTENT_SOURCE_TYPES.INTERVIEW,
  CONTENT_SOURCE_TYPES.DATA,
] as const;

/** Title, type and content of a new source material. */
export function AddSourceForm({
  form,
}: {
  form: SourceForm;
}): React.JSX.Element {
  const t = useTranslations("editorialWorkflow");
  return (
    <form
      className="shrink-0 space-y-3 rounded-md border p-3"
      onSubmit={(event) => void form.addSource(event)}
    >
      <p className="font-medium text-sm">{t("addSourceTitle")}</p>
      <div className="space-y-2">
        <label htmlFor="source-title" className="block text-sm">
          {t("fields.title")}
        </label>
        <input
          id="source-title"
          value={form.title}
          onChange={(event) => form.setTitle(event.target.value)}
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
          value={form.sourceType}
          onChange={(event) => form.setSourceType(event.target.value)}
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
          value={form.content}
          onChange={(event) => form.setContent(event.target.value)}
          rows={4}
          className="w-full resize-none overflow-y-auto rounded-md border border-[var(--color-border)] bg-[var(--color-background)] px-3 py-2 text-sm text-[var(--color-text)]"
          style={{ maxHeight: "120px" }}
          placeholder={t("fields.contentPlaceholder")}
          required
        />
      </div>
      <NeonButton type="submit" size="sm" disabled={form.adding}>
        {form.adding ? t("actions.adding") : t("actions.addSource")}
      </NeonButton>
    </form>
  );
}

/** One source with its extracted key points and the extract action. */
export function SourceItem({
  source,
  onExtract,
}: {
  source: ContentSource;
  onExtract: (sourceId: string) => Promise<void>;
}): React.JSX.Element {
  const t = useTranslations("editorialWorkflow");
  return (
    <div className="rounded-md border p-3 space-y-2">
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
      <NeonButton size="sm" onClick={() => void onExtract(source.id)}>
        {t("actions.extract")}
      </NeonButton>
    </div>
  );
}
