import type { RubricData, RubricColorKey } from "@/features/dashboard/rubrics/types";
import type { NeonRubricCardProps } from "@/components/organisms/neon-rubric-card";
import type { QualityRubric } from "@/features/rubrics/types";

export interface RubricSource {
  title: string;
  category: string;
  score: number;
  maxScore?: number;
  criteria: string[];
}

export function mapRubricToCardProps(rubric: RubricSource): NeonRubricCardProps {
  return {
    title: rubric.title,
    category: rubric.category,
    score: rubric.score,
    maxScore: rubric.maxScore,
    criteria: rubric.criteria,
  };
}

const CONTENT_TYPE_BADGE: Record<string, { badge: string; color: RubricColorKey }> = {
  carousel: { badge: "Carousel", color: "cyan" },
  blog_post: { badge: "Blog", color: "magenta" },
  blog: { badge: "Blog", color: "magenta" },
};

const DEFAULT_BADGE = { badge: "Rubric", color: "teal" as const };

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
      excellent: `≥ ${criterion.min_threshold} (${criterion.scoring_scale})`,
      good: "Meets threshold",
      poor: "Below threshold",
    })),
  };
}
