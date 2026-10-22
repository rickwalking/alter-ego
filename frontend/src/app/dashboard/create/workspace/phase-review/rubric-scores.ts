import { asRecord } from "@/modules/editorial";

/** One criterion's 0-100 score against its threshold. */
export interface RubricCriterionScore {
  id: string;
  name: string;
  score: number;
  threshold: number;
  passed: boolean;
  feedback: string;
}

/** The carousel's rubric evaluation, as the final review shows it. */
export interface RubricScoresView {
  rubricName: string;
  overallScore: number;
  passed: boolean;
  feedback: string;
  criteria: RubricCriterionScore[];
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function numberOr(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function criterion(raw: unknown): RubricCriterionScore | null {
  const row = asRecord(raw);
  if (typeof row.score !== "number") {
    return null;
  }
  return {
    id: text(row.id),
    name: text(row.name) || text(row.id),
    score: row.score,
    threshold: numberOr(row.threshold, 0),
    passed: row.passed === true,
    feedback: text(row.feedback),
  };
}

/**
 * The rubric evaluation in ``rubric_scores`` (rubric name, overall score and a
 * ``criteria`` list), or ``null`` for any other shape.
 */
export function rubricScoresView(
  scores: Record<string, unknown>,
): RubricScoresView | null {
  if (!Array.isArray(scores.criteria)) {
    return null;
  }
  const criteria = scores.criteria
    .map(criterion)
    .filter((row): row is RubricCriterionScore => row !== null);
  return {
    rubricName: text(scores.rubric_name),
    overallScore: numberOr(scores.overall_score, 0),
    passed: scores.passed === true,
    feedback: text(scores.feedback),
    criteria,
  };
}
