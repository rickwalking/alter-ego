"use client";

import { useTranslations } from "next-intl";
import { draftText, outlineTitle } from "../create-phase-review-helpers";
import type { EditorialWorkflowState } from "@/modules/publishing";

export interface DesignPhaseReviewProps {
  state: EditorialWorkflowState;
}

export function DesignPhaseReview({
  state,
}: DesignPhaseReviewProps): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const untitledSlide = t("untitledSlide");

  return (
    <div className="space-y-3 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
      <p className="font-medium">{t("designTitle")}</p>
      <p className="text-[var(--color-text-muted)]">
        {state.design_applied ? t("designReady") : t("designPending")}
      </p>
      {state.outline.length > 0 ? (
        <div className="space-y-2">
          <p className="font-medium text-[var(--color-text)] text-xs uppercase tracking-wide">
            {t("outlineTitle")}
          </p>
          <ol className="list-decimal space-y-1 pl-4 text-[var(--color-text-muted)]">
            {state.outline.map((slide, index) => {
              const title = outlineTitle(slide, untitledSlide);
              return <li key={`${index}-${title}`}>{title}</li>;
            })}
          </ol>
        </div>
      ) : null}
      {state.slide_drafts.length > 0 ? (
        <div className="space-y-2">
          <p className="font-medium text-[var(--color-text)] text-xs uppercase tracking-wide">
            {t("contentTitle")}
          </p>
          {state.slide_drafts.slice(0, 3).map((slide, index) => {
            const text = draftText(slide);
            if (!text) return null;
            return (
              <p
                key={`draft-${index}`}
                className="line-clamp-3 text-[var(--color-text-muted)] text-xs"
              >
                {text}
              </p>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
