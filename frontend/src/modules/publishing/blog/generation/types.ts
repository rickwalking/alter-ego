/** Types of the blog generation hooks and components. */

import type { GenerationState } from "./generation-state";

export interface UseBlogGenerationResult {
  state: GenerationState | null;
  /** The source carousel of a carousel-origin post (visibility link). */
  projectId: string | null;
  retrying: boolean;
  retryFailed: boolean;
  retry: () => Promise<void>;
}

export interface UseCreateBlogFromCarouselResult {
  pending: boolean;
  failed: boolean;
  /** The carousel already has a post: its id (no duplicate is created). */
  existingPostId: string | null;
  create: () => Promise<void>;
}

export interface BlogGenerationStatusProps {
  postId: string;
  /** The editor holds unsaved edits: a retry would replace them, so it is
   * disabled until the owner saves (or discards) them. */
  unsavedChanges?: boolean;
}

export interface BlogGenerationNoticeProps {
  state: GenerationState;
  retrying: boolean;
  retryFailed: boolean;
  unsavedChanges: boolean;
  onRetry: () => void;
}

export type RetryControlProps = Omit<BlogGenerationNoticeProps, "state"> & {
  label: string;
};

export interface CarouselPrivateWarningProps {
  projectId: string | null;
}

export interface CreateBlogFromCarouselProps {
  projectId: string;
  isPublic: boolean;
}

export interface UseOpenBlogEditorResult {
  pending: boolean;
  failed: boolean;
  open: () => Promise<void>;
}

export interface OpenBlogEditorButtonProps {
  projectId: string;
}
