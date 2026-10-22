/**
 * Blog hook shape types (colocated `types.ts`).
 *
 * Per the component-type-location convention
 * (`frontend/scripts/component-type-location.config.mjs`), object-shape types
 * live here rather than inline in the `use-*.ts` hook files.
 */

import type { Dispatch, RefObject, SetStateAction } from "react";

import type { DraftMergeFn, EditorSessionState } from "../lib/editor-session";
import type { LockedPost } from "../blog-editor-requests";
import type { BlogEditorDraft, BlogEditorValidation } from "../editor-content";
import type {
  BlogContentLanguage,
  BlogImageSlotRef,
} from "../lib/editor-document";
import type { BlogPostVersion } from "../components/types";
import type {
  BlogEditorError,
  BlogPost,
  BlogPostUpdatePayload,
  BlogVoicePersona,
} from "../types";

/** Re-export: the editor error shape lives in the domain types. */
export type { BlogEditorError };

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

/** The loaded post, the draft as loaded (`original`) and the edited draft. */
export type EditorSession = EditorSessionState;

export type DraftMerge = DraftMergeFn;

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
  /** Restores the version; resolves with the failure or `null` on success. */
  handleRestore: (versionNumber: number) => Promise<BlogEditorError | null>;
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
  /** A slot action is running: review/publish controls wait for it. */
  anyPending: boolean;
  generateImage: (
    slot: BlogImageSlotRef,
    prompt: string | null,
  ) => Promise<void>;
  rewrite: (sectionId: string) => Promise<void>;
  generateTranslation: () => Promise<void>;
}

export interface BlogReviewActions {
  pending: boolean;
  /** The last failed review/publish/schedule action (shown in the review bar). */
  error: BlogEditorError | null;
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

/** One slot action: its status key, the request and how to merge its answer. */
export interface SlotRun {
  key: string;
  task: (target: LockedPost) => Promise<BlogPost>;
  merge: DraftMerge;
}

/** Per-slot status plus the runner that drives it. */
export interface SlotRunner {
  status: Record<string, SlotStatus>;
  run: (slotRun: SlotRun) => Promise<void>;
}

/** Arguments of ``useBlogAi().suggest``. */
export interface SuggestArgs {
  text: string;
  suggestionType: string;
  context?: string;
}

/** The list state ``useBlogPosts`` keeps. */
export interface BlogPostList {
  posts: BlogPost[];
  setPosts: Dispatch<SetStateAction<BlogPost[]>>;
  total: number;
  loading: boolean;
  error: string | null;
  filters: BlogPostFilters;
  setFilters: Dispatch<SetStateAction<BlogPostFilters>>;
  fetchPosts: (activeFilters?: BlogPostFilters) => Promise<void>;
}

/** What saving/restoring one editor session needs. */
export interface EditorPersistenceDeps {
  session: EditorSession | null;
  setSession: Dispatch<SetStateAction<EditorSession | null>>;
  latest: RefObject<EditorSession | null>;
  payload: BlogPostUpdatePayload | null;
  validation: BlogEditorValidation | null;
}

/** Save + restore for the blog editor. */
export interface EditorPersistence {
  persist: () => Promise<BlogPost | null>;
  handleRestore: (versionNumber: number) => Promise<BlogEditorError | null>;
  saving: boolean;
  error: BlogEditorError | null;
  setError: Dispatch<SetStateAction<BlogEditorError | null>>;
}

/** Draft-derived editor values. */
export interface DraftState {
  draft: BlogEditorDraft | null;
  validation: BlogEditorValidation | null;
  payload: BlogPostUpdatePayload | null;
}

/** The public blog post made from one carousel. */
export interface CarouselPublicPostHref {
  /** Public URL of the carousel's published blog post, or null when none. */
  href: string | null;
  /** Look the post up again (e.g. right after a site publish). */
  refetch: () => Promise<unknown>;
}
