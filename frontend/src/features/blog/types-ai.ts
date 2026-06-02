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

export interface EditorialWorkflowState {
  project_id: string;
  current_phase: string;
  phase_status: string;
  research_findings: Record<string, unknown>[];
  outline: Record<string, unknown>[];
  slide_drafts: Record<string, unknown>[];
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
}
