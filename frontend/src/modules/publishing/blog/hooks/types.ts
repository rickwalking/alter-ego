/**
 * Blog hook shape types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), object-shape types
 * live here rather than inline in the `use-*.ts` hook files.
 */

import type { Dispatch, SetStateAction } from "react";

import type { BlogPostVersion } from "../components/types";
import type { BlogPostMutationErrorCode } from "../constants";
import type { BlogEditorValidation } from "../editor-content";
import type { BlogPost } from "../types";

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

/** Why an editor save failed (AE-0411): a backend guard code or a generic failure. */
export type BlogEditorSaveError = BlogPostMutationErrorCode | "failed";

export interface UseBlogPostEditorResult {
  post: BlogPost | undefined;
  loading: boolean;
  /** The detail request failed (network/5xx); a 404 is `post` undefined. */
  loadFailed: boolean;
  saving: boolean;
  title: string;
  setTitle: Dispatch<SetStateAction<string>>;
  excerpt: string;
  setExcerpt: Dispatch<SetStateAction<string>>;
  bodyText: string;
  setBodyText: Dispatch<SetStateAction<string>>;
  selectedText: string;
  setSelectedText: Dispatch<SetStateAction<string>>;
  /** Client-side checks mirroring the backend 422 rules. */
  validation: BlogEditorValidation;
  saveError: BlogEditorSaveError | null;
  /** Resolves `true` when saved (or nothing changed); never rejects. */
  handleSave: () => Promise<boolean>;
  handleRestore: (version: BlogPostVersion) => void;
}

export interface BlogAiImproveParams {
  text: string;
  action: string;
  context?: string;
  personaId?: string;
}
