/** Types of the blog generation hooks and components (AE-0425). */

import type { GenerationState } from "./generation-state";

export type UseBlogGenerationResult = {
  state: GenerationState | null;
  /** The source carousel of a carousel-origin post (visibility link). */
  projectId: string | null;
  retrying: boolean;
  retryFailed: boolean;
  retry: () => Promise<void>;
};

export type UseCreateBlogFromCarouselResult = {
  pending: boolean;
  failed: boolean;
  /** The carousel already has a post: its id (no duplicate is created). */
  existingPostId: string | null;
  create: () => Promise<void>;
};

export type BlogGenerationStatusProps = {
  postId: string;
};

export type BlogGenerationNoticeProps = {
  state: GenerationState;
  retrying: boolean;
  retryFailed: boolean;
  onRetry: () => void;
};

export type CarouselPrivateWarningProps = {
  projectId: string | null;
};

export type CreateBlogFromCarouselProps = {
  projectId: string;
  isPublic: boolean;
};
