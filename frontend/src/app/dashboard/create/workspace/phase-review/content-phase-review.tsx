"use client";

import { useTranslations } from "next-intl";
import {
  asString,
  draftText,
  outlineTitle,
} from "../create-phase-review-helpers";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";

export interface ContentPhaseReviewProps {
  state: EditorialWorkflowState;
}

export function ContentPhaseReview({
  state,
}: ContentPhaseReviewProps): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const untitledSlide = t("untitledSlide");

  if (state.slide_drafts.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-[var(--color-border)] p-3 text-[var(--color-text-muted)] text-sm">
        {t("emptyPhase")}
      </div>
    );
  }

  return (
    <div className="space-y-2 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
      <p className="font-medium">{t("contentTitle")}</p>
      <div className="space-y-3">
        {state.slide_drafts.map((slide, index) => {
          const title = outlineTitle(slide, untitledSlide);
          const text = draftText(slide);
          const key = `${asString(slide.slide_index) || index}-${title}`;
          return (
            <div
              key={key}
              className="space-y-1 border-[var(--color-border)] border-b pb-2 last:border-0"
            >
              <p className="font-medium text-[var(--color-text)]">{title}</p>
              {text ? (
                <p className="whitespace-pre-wrap text-[var(--color-text-muted)] text-xs">
                  {text}
                </p>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
