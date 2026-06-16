"use client";

import { useTranslations } from "next-intl";
import type { EditorialWorkflowState } from "@/modules/publishing";

export interface ImagesPhaseReviewProps {
  state: EditorialWorkflowState;
}

export function ImagesPhaseReview({
  state,
}: ImagesPhaseReviewProps): React.ReactElement | null {
  const t = useTranslations("editorialWorkflow.review");

  if ((state.image_assets?.length ?? 0) === 0) {
    return null;
  }

  return (
    <div className="space-y-2 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
      <p className="font-medium">{t("imagesTitle")}</p>
      <ul className="list-disc space-y-1 pl-4 text-[var(--color-text-muted)]">
        {state.image_assets?.map((asset) => (
          <li key={asset} className="break-all font-mono text-xs">
            {asset}
          </li>
        ))}
      </ul>
    </div>
  );
}
