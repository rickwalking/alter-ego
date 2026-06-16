/**
 * Blog hook shape types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), object-shape types
 * live here rather than inline in the `use-*.ts` hook files.
 */

export interface AccessibilityIssue {
  code: string;
  message: string;
  severity: string;
}

export interface AccessibilityResult {
  overall_score: number;
  passed: boolean;
  severity: string;
  issues: AccessibilityIssue[];
}

export interface UseBlogAiState {
  loading: boolean;
  error: string | null;
}

export interface BlogPostFilters {
  status?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface EditorShortcutHandlers {
  onSave?: () => void;
  onSubmitReview?: () => void;
  onAiSuggest?: () => void;
  onShowHelp?: () => void;
}

export interface SeoAnalysisResult {
  overall_score: number;
  passed: boolean;
  severity: string;
  issues: Array<{ code: string; message: string }>;
  suggestions: string[];
}
