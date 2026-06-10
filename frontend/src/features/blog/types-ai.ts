/** Types for blog AI assistance. */

export interface BlogAiSuggestResult {
  original_text: string;
  suggested_text: string;
  suggestion_type: string;
  explanation: string;
}

export interface BlogAiImproveResult {
  original_text: string;
  improved_text: string;
  action: string;
}

export interface BlogGenerateImageResult {
  prompt: string;
  image_url: string;
}

export interface VoiceScoreResult {
  tone_match: number;
  sentence_structure_match: number;
  opinion_strength: number;
  originality: number;
  human_authenticity: number;
  overall: number;
  suggestions: string[];
  passed: boolean;
}

export interface RubricEvaluationResult {
  rubric_id: string;
  overall_score: number;
  passed: boolean;
  scores: Record<string, { score: number; weight: number; passed: boolean }>;
  feedback: Record<string, unknown>[];
}

export interface ContentSource {
  id: string;
  project_id?: string | null;
  title: string;
  content: string;
  source_type: string;
  extracted_key_points: string[];
  tags: string[];
  is_primary: boolean;
}

export interface SlideValidationViolation {
  code: string;
  message: string;
  slide_index?: number | null;
  locale?: string | null;
  field?: string | null;
}

export interface SlideValidationReport {
  validation_status: string;
  validated_at: string;
  blocking: boolean;
  violations: SlideValidationViolation[];
}

export interface LocalizedSlideReview {
  slide_index: number;
  slide_type: string;
  presentation_pt: Record<string, unknown>;
  presentation_en: Record<string, unknown>;
}

export interface SlideImagePrompt {
  slide_index: number;
  title: string;
  image_prompt: string;
  rendered_image_prompt?: string | null;
  image_generation_key?: string | null;
  image_prompt_hash?: string | null;
  image_provider?: string | null;
  image_model?: string | null;
  image_style?: string | null;
  theme_name?: string | null;
  theme_colors?: Record<string, string> | null;
}

export type WorkflowPhaseStatus =
  | "pending"
  | "in_progress"
  | "awaiting_human"
  | "approved"
  | "rejected"
  | "failed";

export interface EditorialWorkflowState {
  project_id: string;
  current_phase: string;
  phase_status: WorkflowPhaseStatus;
  research_findings: Record<string, unknown>[];
  outline: Record<string, unknown>[];
  slide_drafts: Record<string, unknown>[];
  slide_image_prompts?: SlideImagePrompt[] | null;
  image_assets?: string[];
  design_applied?: boolean;
  phase_progress?: Record<string, unknown> | null;
  rubric_scores?: Record<string, unknown>;
  caption?: string;
  blog_markdown?: string;
  linkedin_post_pt?: string;
  linkedin_post_en?: string;
  status: string;
  workflow_status?: string;
  persona_scores?: Record<string, unknown>;
  lock_version?: number;
  error_message?: string;
  presentation_policy_version?: string | null;
  localized_slides?: LocalizedSlideReview[];
  presentation_validation?: SlideValidationReport | null;
}
