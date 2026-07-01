"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  BLOG_POST_ERR_CAROUSEL_DELETE_BLOCKED,
  BlogPostMutationError,
} from "@/modules/publishing";
import { BLOG_POSTS_I18N_NAMESPACE } from "@/modules/editorial-operations";
import type { DashboardBlogPost } from "@/modules/editorial-operations";
import type { BlogPostActionHandlers } from "@/app/dashboard/blog-posts/types";

interface UseBlogPostActionsInput {
  deletePost: (id: string, lockVersion: number) => Promise<boolean>;
  unpublish: (id: string, lockVersion: number) => Promise<unknown>;
}

interface UseBlogPostActionsResult {
  actions: BlogPostActionHandlers;
  deleteTarget: DashboardBlogPost | null;
  actionError: string | null;
  confirmDelete: () => Promise<void>;
  cancelDelete: () => void;
}

/**
 * Page-level state machine for the card management actions (AE-0296):
 * delete goes through an explicit confirmation dialog; hide (unpublish)
 * fires directly; guard failures surface as localized error copy.
 */
export function useBlogPostActions({
  deletePost,
  unpublish,
}: UseBlogPostActionsInput): UseBlogPostActionsResult {
  const t = useTranslations(BLOG_POSTS_I18N_NAMESPACE);
  const [deleteTarget, setDeleteTarget] = useState<DashboardBlogPost | null>(
    null,
  );
  const [actionError, setActionError] = useState<string | null>(null);

  const mapError = (err: unknown): string => {
    if (err instanceof BlogPostMutationError) {
      return err.code === BLOG_POST_ERR_CAROUSEL_DELETE_BLOCKED
        ? t("errors.carouselDeleteBlocked")
        : t("errors.versionConflict");
    }
    return t("errors.actionFailed");
  };

  const confirmDelete = async (): Promise<void> => {
    if (!deleteTarget) {
      return;
    }
    setActionError(null);
    try {
      await deletePost(deleteTarget.id, deleteTarget.lockVersion);
    } catch (err) {
      setActionError(mapError(err));
    } finally {
      setDeleteTarget(null);
    }
  };

  const handleHide = async (post: DashboardBlogPost): Promise<void> => {
    setActionError(null);
    try {
      await unpublish(post.id, post.lockVersion);
    } catch (err) {
      setActionError(mapError(err));
    }
  };

  return {
    actions: {
      onDelete: (post: DashboardBlogPost) => setDeleteTarget(post),
      onHide: (post: DashboardBlogPost) => void handleHide(post),
    },
    deleteTarget,
    actionError,
    confirmDelete,
    cancelDelete: () => setDeleteTarget(null),
  };
}
