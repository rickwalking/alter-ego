"use client";

import { useTranslations } from "next-intl";
import { asString, outlineTitle } from "../create-phase-review-helpers";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";

export interface OutlinePhaseReviewProps {
  state: EditorialWorkflowState;
}

export function OutlinePhaseReview({
  state,
}: OutlinePhaseReviewProps): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const untitledSlide = t("untitledSlide");

  if (state.outline.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-[var(--color-border)] p-3 text-[var(--color-text-muted)] text-sm">
        {t("emptyPhase")}
      </div>
    );
  }

  return (
    <div className="space-y-2 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
      <p className="font-medium">{t("outlineTitle")}</p>
      <ol className="list-decimal space-y-2 pl-4">
        {state.outline.map((slide, index) => {
          const title = outlineTitle(slide, untitledSlide);
          const key = `${asString(slide.slide_index) || index}-${title}`;
          const points = Array.isArray(slide.key_points)
            ? slide.key_points.filter((p): p is string => typeof p === "string")
            : [];
          return (
            <li key={key} className="space-y-0.5">
              <p className="font-medium text-[var(--color-text)]">{title}</p>
              {points.length > 0 ? (
                <p className="text-[var(--color-text-muted)] text-xs">
                  {points.join(" · ")}
                </p>
              ) : null}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
