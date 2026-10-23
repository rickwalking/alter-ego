"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import type { EditorialWorkflowState } from "@/modules/publishing";
import { resolveRubricScores } from "../create-phase-review-helpers";
import { rubricScoresView, type RubricScoresView } from "./rubric-scores";

const MUTED = "text-[var(--color-text-muted)]";
const BELOW = "text-destructive";

interface QualityTabProps {
  readonly state: EditorialWorkflowState;
  readonly emptyText: string;
}

interface RubricScoresPanelProps {
  readonly view: RubricScoresView;
}

/** The rubric, its overall score and each criterion's score vs threshold. */
function RubricScoresPanel({
  view,
}: RubricScoresPanelProps): React.JSX.Element {
  const t = useTranslations("editorialWorkflow.review.finalReview.rubric");
  return (
    <div className="space-y-2">
      <p className="font-medium">
        {t("summary", { name: view.rubricName, score: view.overallScore })}
      </p>
      <p className={view.passed ? MUTED : BELOW}>
        {view.passed ? t("passed") : t("failed")}
      </p>
      <ul className="space-y-2">
        {view.criteria.map((row) => (
          <li
            key={row.id}
            className="space-y-0.5 rounded-md border border-[var(--color-border)] p-2"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">{row.name}</span>
              <span className={row.passed ? MUTED : BELOW}>
                {t("score", { score: row.score, threshold: row.threshold })}
              </span>
            </div>
            {!row.passed && (
              <p className={cn("text-xs", BELOW)}>{t("belowThreshold")}</p>
            )}
            {row.feedback && (
              <p className={cn("text-xs", MUTED)}>{row.feedback}</p>
            )}
          </li>
        ))}
      </ul>
      {view.feedback && <p className={cn("text-xs", MUTED)}>{view.feedback}</p>}
    </div>
  );
}

/**
 * The final review "Qualidade" tab: the carousel's rubric scores (each
 * criterion flagged when below its threshold), any other score map as
 * name/value rows, or the empty note.
 */
export function QualityTab({
  state,
  emptyText,
}: QualityTabProps): React.JSX.Element {
  const scores = resolveRubricScores(state);
  const view = rubricScoresView(scores);
  if (view) {
    return <RubricScoresPanel view={view} />;
  }
  const entries = Object.entries(scores);
  if (entries.length === 0) {
    return <p className={MUTED}>{emptyText}</p>;
  }
  return (
    <ul className="space-y-1">
      {entries.map(([name, value]) => (
        <li
          key={name}
          className={cn("flex items-center justify-between gap-2", MUTED)}
        >
          <span className="font-medium capitalize">
            {name.replaceAll("_", " ")}
          </span>
          <span>
            {typeof value === "string" ? value : JSON.stringify(value)}
          </span>
        </li>
      ))}
    </ul>
  );
}
