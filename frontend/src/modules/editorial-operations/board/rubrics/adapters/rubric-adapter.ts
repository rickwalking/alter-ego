import type {
  RubricData,
  RubricColorKey,
} from "@/modules/editorial-operations/board/rubrics/types";
import type { NeonRubricCardProps, QualityRubric } from "@/modules/quality";

export interface RubricSource {
  title: string;
  category: string;
  score: number;
  maxScore?: number;
  criteria: string[];
}

export function mapRubricToCardProps(
  rubric: RubricSource,
): NeonRubricCardProps {
  return {
    title: rubric.title,
    category: rubric.category,
    score: rubric.score,
    maxScore: rubric.maxScore,
    criteria: rubric.criteria,
  };
}

const CONTENT_TYPE_BADGE: Record<
  string,
  { badge: string; color: RubricColorKey }
> = {
  carousel: { badge: "Carousel", color: "cyan" },
  blog_post: { badge: "Blog", color: "magenta" },
  blog: { badge: "Blog", color: "magenta" },
};

const DEFAULT_BADGE = { badge: "Rubric", color: "teal" as const };
const PERCENT = 100;

/** A criterion threshold (a 0-1 fraction of its scale) as "≥ 70% (0-100)". */
export function thresholdLabel(
  minThreshold: number,
  scoringScale: string,
): string {
  return `≥ ${Math.round(minThreshold * PERCENT)}% (${scoringScale})`;
}

export function mapQualityRubricToPanelData(rubric: QualityRubric): RubricData {
  const contentType = rubric.applicable_content_types[0] ?? "general";
  const badgeMeta = CONTENT_TYPE_BADGE[contentType] ?? DEFAULT_BADGE;

  return {
    badge: badgeMeta.badge,
    badgeColor: badgeMeta.color,
    title: rubric.name,
    weight: rubric.is_default ? "1.0 (default)" : "1.0",
    status: "active",
    criteria: rubric.criteria.map((criterion) => ({
      name: criterion.name,
      description: criterion.description,
      excellent: thresholdLabel(
        criterion.min_threshold,
        criterion.scoring_scale,
      ),
      good: "Meets threshold",
      poor: "Below threshold",
    })),
  };
}
