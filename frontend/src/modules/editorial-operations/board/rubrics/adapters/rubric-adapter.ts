import type {
  RubricColorKey,
  RubricContentTypeTag,
  RubricData,
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

const CONTENT_TYPE_COLOR: Readonly<Record<string, RubricColorKey>> = {
  carousel: "cyan",
  blog_post: "magenta",
};

const DEFAULT_CONTENT_TYPE_COLOR: RubricColorKey = "teal";
const PERCENT = 100;

/** A criterion threshold (a 0-1 fraction of its scale) as a whole percentage. */
export function thresholdPercent(minThreshold: number): number {
  return Math.round(minThreshold * PERCENT);
}

/** Every content type the rubric applies to, each with its badge colour. */
function contentTypeTags(types: readonly string[]): RubricContentTypeTag[] {
  return types.map((type) => ({
    type,
    color: CONTENT_TYPE_COLOR[type] ?? DEFAULT_CONTENT_TYPE_COLOR,
  }));
}

/** The rubric card data: only what the API returns, untranslated keys kept. */
export function mapQualityRubricToPanelData(rubric: QualityRubric): RubricData {
  return {
    title: rubric.name,
    contentTypes: contentTypeTags(rubric.applicable_content_types),
    isDefault: rubric.is_default,
    criteria: rubric.criteria.map((criterion) => ({
      name: criterion.name,
      description: criterion.description,
      weight: criterion.weight,
      thresholdPercent: thresholdPercent(criterion.min_threshold),
      scoringScale: criterion.scoring_scale,
    })),
  };
}
