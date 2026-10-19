/**
 * Blog hook shape types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), object-shape types
 * live here rather than inline in the `use-*.ts` hook files.
 */

import type { Dispatch, SetStateAction } from "react";

import type { BlogDocument } from "@/schemas/blog-document";
import type { BlogEditorErrorKind } from "@/constants/blog-editor";
import type { LockedPost } from "../blog-editor-requests";
import type { BlogEditorDraft, BlogEditorValidation } from "../editor-content";
import type {
  BlogContentLanguage,
  BlogImageSlotRef,
} from "../lib/editor-document";
import type { BlogPostVersion } from "../components/types";
import type { BlogPost, BlogVoicePersona } from "../types";

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

/** A failed editor request (AE-0424): the typed kind + the API detail code. */
export interface BlogEditorError {
  kind: BlogEditorErrorKind;
  detail: string | null;
}

/** The loaded post, the draft as loaded (`original`) and the edited draft. */
export interface EditorSession {
  base: BlogPost;
  /** `null` when the stored content is not `blog.v2` (migration pending). */
  original: BlogEditorDraft | null;
  draft: BlogEditorDraft | null;
}

export type DraftMerge = (
  draftDoc: BlogDocument,
  serverDoc: BlogDocument,
) => BlogDocument;

export interface UseBlogPostEditorResult {
  post: BlogPost | undefined;
  loading: boolean;
  /** The detail request failed (network/5xx); a 404 is `post` undefined. */
  loadFailed: boolean;
  draft: BlogEditorDraft | null;
  /** The content language being edited (independent of the UI locale). */
  language: BlogContentLanguage;
  setLanguage: Dispatch<SetStateAction<BlogContentLanguage>>;
  updateDraft: (edit: (current: BlogEditorDraft) => BlogEditorDraft) => void;
  /** Client-side checks mirroring the backend 422 rules. */
  validation: BlogEditorValidation | null;
  /** The draft differs from the loaded post (drives the unsaved guard). */
  dirty: boolean;
  saving: boolean;
  error: BlogEditorError | null;
  setError: Dispatch<SetStateAction<BlogEditorError | null>>;
  /** Resolves `true` when saved (or nothing changed); never rejects. */
  handleSave: () => Promise<boolean>;
  /** Save pending edits first; the locked post to act on, or `null`. */
  ensureSaved: () => Promise<LockedPost | null>;
  /** Take a slot action's answer: server state, draft keeps other edits. */
  applyServerPost: (post: BlogPost, merge: DraftMerge) => void;
  /** Take a workflow/restore answer wholesale. */
  replaceFromServer: (post: BlogPost) => void;
  /** Re-read the post (after a multi-step flow failed midway). */
  reload: () => Promise<void>;
  handleRestore: (versionNumber: number) => Promise<boolean>;
}

export interface BlogAiImproveParams {
  text: string;
  action: string;
  context?: string;
  personaId?: string;
}

/** Pending/error state of one image, rewrite or translation slot. */
export interface SlotStatus {
  pending: boolean;
  error: BlogEditorError | null;
}

export interface BlogEditorSlotActions {
  statusOf: (key: string) => SlotStatus;
  generateImage: (
    slot: BlogImageSlotRef,
    prompt: string | null,
  ) => Promise<void>;
  rewrite: (sectionId: string) => Promise<void>;
  generateTranslation: () => Promise<void>;
}

export interface BlogReviewActions {
  /** `BLOG_ALLOW_SELF_REVIEW`: "Publish now" instead of explicit steps. */
  allowSelfReview: boolean;
  pending: boolean;
  submitForReview: (reviewerId: string | null) => Promise<void>;
  approve: () => Promise<void>;
  reject: (reason: string) => Promise<void>;
  publish: () => Promise<void>;
  publishNow: () => Promise<void>;
  unpublish: () => Promise<void>;
  schedule: (scheduledAtIso: string) => Promise<void>;
  cancelSchedule: () => Promise<void>;
}

export interface BlogEditorData {
  versions: BlogPostVersion[];
  versionsLoading: boolean;
  personas: BlogVoicePersona[];
  /** The chosen voice persona (default: the first one), `null` when none. */
  personaId: string | null;
  setPersonaId: (personaId: string | null) => void;
}
