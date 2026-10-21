"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { BLOG_POSTS_I18N_NAMESPACE } from "@/modules/editorial-operations";
import {
  BLOG_POST_ERR_SLUG_CONFLICT,
  BlogPostMutationError,
  useBlogPosts,
} from "@/modules/publishing";

interface UseNewBlogPostResult {
  creating: boolean;
  createError: string | null;
  handleNewPost: () => Promise<void>;
}

/**
 * Encapsulates the "create a draft and navigate to the editor" action used by
 * the Blog Posts dashboard top bar. It flips `creating` on, creates a draft
 * titled with the localized "Untitled draft", navigates on success, and on
 * failure resets `creating` and exposes a localized error.
 */
export function useNewBlogPost(
  create: ReturnType<typeof useBlogPosts>["create"],
): UseNewBlogPostResult {
  const router = useRouter();
  const t = useTranslations(BLOG_POSTS_I18N_NAMESPACE);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const handleNewPost = async (): Promise<void> => {
    setCreating(true);
    setCreateError(null);
    try {
      const post = await create({
        title: t("untitledDraft"),
        content: { body: "" },
        excerpt: "",
      });
      router.push(DASHBOARD_ROUTES.BLOG_POST_EDIT(post.id));
    } catch (err) {
      const slugClash =
        err instanceof BlogPostMutationError &&
        err.code === BLOG_POST_ERR_SLUG_CONFLICT;
      setCreateError(
        slugClash ? t("errors.slugConflict") : t("errors.createFailed"),
      );
      setCreating(false);
    }
  };

  return { creating, createError, handleNewPost };
}
