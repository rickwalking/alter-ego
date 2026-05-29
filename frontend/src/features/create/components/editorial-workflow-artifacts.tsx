"use client";

import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";

interface EditorialWorkflowArtifactsProps {
  state: EditorialWorkflowState | null;
}

function countItems(items: Record<string, unknown>[] | undefined): number {
  return items?.length ?? 0;
}

export function EditorialWorkflowArtifacts({
  state,
}: EditorialWorkflowArtifactsProps): React.JSX.Element | null {
  const t = useTranslations("editorialWorkflow.artifacts");

  if (!state) {
    return null;
  }

  const outlineCount = countItems(state.outline);
  const draftCount = countItems(state.slide_drafts);
  const imageCount = state.image_assets?.length ?? 0;

  if (outlineCount === 0 && draftCount === 0 && imageCount === 0) {
    return null;
  }

  return (
    <div className="space-y-2 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
      <p className="font-medium">{t("title")}</p>
      <ul className="space-y-1 text-[var(--color-text-muted)]">
        {outlineCount > 0 && (
          <li>{t("outlineSlides", { count: outlineCount })}</li>
        )}
        {draftCount > 0 && <li>{t("contentDrafts", { count: draftCount })}</li>}
        {state.design_applied && (
          <li className="flex items-center gap-2">
            {t("designApplied")}
            <Badge variant="secondary">{t("ready")}</Badge>
          </li>
        )}
        {imageCount > 0 && (
          <li>{t("imagesGenerated", { count: imageCount })}</li>
        )}
      </ul>
    </div>
  );
}
