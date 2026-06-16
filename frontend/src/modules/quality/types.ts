/**
 * Quality Rubric Types
 */

export interface RubricCriterion {
  id: string;
  name: string;
  description: string;
  weight: number;
  evaluation_method: string;
  min_threshold: number;
  scoring_scale: string;
  prompt_template: string;
}

export interface QualityRubric {
  id: string;
  name: string;
  description?: string | null;
  criteria: RubricCriterion[];
  applicable_content_types: string[];
  is_default: boolean;
  created_at: string;
  updated_at: string;
  version: number;
}

export interface QualityRubricCreatePayload {
  name: string;
  description?: string | null;
  criteria?: RubricCriterion[];
  applicable_content_types?: string[];
  is_default?: boolean;
}

export interface QualityRubricUpdatePayload {
  name?: string | null;
  description?: string | null;
  criteria?: RubricCriterion[] | null;
  applicable_content_types?: string[] | null;
  is_default?: boolean | null;
}

export interface RubricEvaluationScore {
  criterion_id: string;
  score: number;
  weight: number;
  passed: boolean;
}

export interface RubricEvaluationResponse {
  rubric_id: string;
  content_id: string;
  content_type: string;
  evaluated_at: string;
  scores: Record<string, RubricEvaluationScore>;
  overall_score: number;
  passed: boolean;
  feedback: Record<string, unknown>[];
}
