import type { NeonRubricCardProps } from "@/components/organisms/neon-rubric-card";

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
