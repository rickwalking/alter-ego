"use client";

import { useTranslations } from "next-intl";
import { asString } from "../create-phase-review-helpers";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";

export interface ResearchPhaseReviewProps {
  state: EditorialWorkflowState;
}

export function ResearchPhaseReview({
  state,
}: ResearchPhaseReviewProps): React.ReactElement | null {
  const t = useTranslations("editorialWorkflow.review");

  if (state.research_findings.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
      <p className="font-medium">{t("researchTitle")}</p>
      <ul className="space-y-2">
        {state.research_findings.map((finding, index) => {
          const source =
            asString(finding.source) ||
            t("findingFallback", { index: index + 1 });
          const points = Array.isArray(finding.key_points)
            ? finding.key_points.filter(
                (p): p is string => typeof p === "string",
              )
            : [];
          return (
            <li key={source} className="space-y-1">
              <p className="font-medium text-[var(--color-text)]">{source}</p>
              {points.length > 0 ? (
                <ul className="list-disc space-y-0.5 pl-4 text-[var(--color-text-muted)]">
                  {points.map((point) => (
                    <li key={point}>{point}</li>
                  ))}
                </ul>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
