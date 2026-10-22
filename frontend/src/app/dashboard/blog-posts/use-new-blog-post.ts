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
import type { UseNewBlogPostResult } from "./types";

/**
 * The "New Post" form of the Blog Posts top bar. Opening it creates nothing;
 * only a submit with a non-blank title creates the draft and opens its editor.
 * A failed create keeps the form open with a localized error.
 */
export function useNewBlogPost(
  create: ReturnType<typeof useBlogPosts>["create"],
): UseNewBlogPostResult {
  const router = useRouter();
  const t = useTranslations(BLOG_POSTS_I18N_NAMESPACE);
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const trimmedTitle = title.trim();

  const show = (): void => {
    setTitle("");
    setCreateError(null);
    setOpen(true);
  };

  const submit = async (): Promise<void> => {
    if (!trimmedTitle) {
      return;
    }
    setCreating(true);
    setCreateError(null);
    try {
      const post = await create({
        title: trimmedTitle,
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

  return {
    open,
    title,
    setTitle,
    canSubmit: trimmedTitle.length > 0 && !creating,
    creating,
    createError,
    show,
    hide: () => setOpen(false),
    submit,
  };
}
