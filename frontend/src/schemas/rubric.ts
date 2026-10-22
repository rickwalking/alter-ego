import { z } from "zod";

/** Mirrors `QualityRubricCreate.name` (1–255 characters). */
export const RUBRIC_NAME_MAX = 255;

/** `EvaluationMethod` values of the backend domain model. */
export const EVALUATION_METHODS = [
  "ai_auto",
  "human_required",
  "hybrid",
] as const;

/** `ScoringScale` values of the backend domain model. */
export const SCORING_SCALES = [
  "0-100",
  "1-10",
  "pass_fail",
  "grade_a_f",
] as const;

/** Content types a rubric can apply to (the backend's default is carousel). */
export const RUBRIC_CONTENT_TYPES = ["carousel", "blog_post"] as const;

export type EvaluationMethod = (typeof EVALUATION_METHODS)[number];
export type ScoringScale = (typeof SCORING_SCALES)[number];

/** `weight` and `min_threshold` are `ge=0.0, le=1.0` on the backend. */
const unitInterval = z.number().min(0).max(1);

/** One criterion, as `RubricCriterion` accepts it. */
export const rubricCriterionSchema = z.object({
  id: z.string().min(1),
  name: z.string().trim().min(1),
  description: z.string(),
  weight: unitInterval,
  evaluation_method: z.enum(EVALUATION_METHODS),
  min_threshold: unitInterval,
  scoring_scale: z.enum(SCORING_SCALES),
  prompt_template: z.string(),
});

/** The create/update payload the rubric form sends. */
export const rubricFormSchema = z.object({
  name: z.string().trim().min(1).max(RUBRIC_NAME_MAX),
  description: z.string(),
  applicable_content_types: z.array(z.string().min(1)).min(1),
  criteria: z.array(rubricCriterionSchema).min(1),
});
