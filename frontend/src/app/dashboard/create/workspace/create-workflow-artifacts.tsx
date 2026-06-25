"use client";
import { NeonBadge } from "@/components/atoms/neon-badge";

import { useTranslations } from "next-intl";
import type { EditorialWorkflowState } from "@/modules/publishing";

interface CreateWorkflowArtifactsProps {
  state: EditorialWorkflowState | null;
}

function countItems(items: Record<string, unknown>[] | undefined): number {
  return items?.length ?? 0;
}

export function CreateWorkflowArtifacts({
  state,
}: CreateWorkflowArtifactsProps): React.JSX.Element | null {
  const t = useTranslations("editorialWorkflow.artifacts");

  if (!state) {
    return null;
  }

  const outlineCount = countItems(state.outline);
  const draftCount = countItems(state.slide_drafts);
  const promptCount = state.slide_image_prompts?.length ?? 0;
  const imageCount = state.image_assets?.length ?? 0;

  if (
    outlineCount === 0 &&
    draftCount === 0 &&
    promptCount === 0 &&
    imageCount === 0
  ) {
    return null;
  }

  return (
    <div
      className="space-y-2 rounded-md p-3 text-sm"
      style={{
        border: "1px solid rgba(255,255,255,0.06)",
        background: "#0d1324",
      }}
    >
      <p className="font-medium" style={{ color: "rgba(255,255,255,0.88)" }}>
        {t("title")}
      </p>
      <ul className="space-y-1" style={{ color: "rgba(255,255,255,0.55)" }}>
        {outlineCount > 0 && (
          <li>{t("outlineSlides", { count: outlineCount })}</li>
        )}
        {draftCount > 0 && <li>{t("contentDrafts", { count: draftCount })}</li>}
        {promptCount > 0 && (
          <li>{t("imagePromptsReady", { count: promptCount })}</li>
        )}
        {state.design_applied && (
          <li className="flex items-center gap-2">
            {t("designApplied")}
            <NeonBadge variant="green" dot>
              {t("ready")}
            </NeonBadge>
          </li>
        )}
        {imageCount > 0 && (
          <li>{t("imagesGenerated", { count: imageCount })}</li>
        )}
      </ul>
    </div>
  );
}
