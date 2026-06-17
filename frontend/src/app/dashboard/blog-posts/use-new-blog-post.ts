"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { useBlogPosts } from "@/modules/publishing";

type UseNewBlogPostResult = {
  creating: boolean;
  handleNewPost: () => Promise<void>;
};

/**
 * Encapsulates the "create a draft and navigate to the editor" action used by
 * the Blog Posts dashboard top bar. Behavior is identical to the original
 * inline handler: it flips `creating` on, creates an empty draft, navigates on
 * success, and resets `creating` only on failure.
 */
export function useNewBlogPost(
  create: ReturnType<typeof useBlogPosts>["create"],
): UseNewBlogPostResult {
  const router = useRouter();
  const [creating, setCreating] = useState(false);

  const handleNewPost = async (): Promise<void> => {
    setCreating(true);
    try {
      const post = await create({
        title: "Untitled draft",
        content: { blocks: [] },
        excerpt: "",
      });
      router.push(DASHBOARD_ROUTES.BLOG_POST_EDIT(post.id));
    } catch {
      setCreating(false);
    }
  };

  return { creating, handleNewPost };
}
