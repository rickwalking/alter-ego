"use client";

/**
 * Review, publish and schedule controls of the blog editor (AE-0424).
 *
 * They call the existing `blog_post_workflow` routes through the status
 * guards (a draft cannot jump to `published`: the 400 is shown, not
 * swallowed). The author may review their own post (AE-0441), so "Publish
 * now" on a draft runs submit-review (the author as reviewer) -> approve ->
 * publish in one flow.
 */

import { useState } from "react";

import { BLOG_EDITOR_ERROR_KINDS } from "@/constants/blog-editor";
import {
  approvePost,
  BlogEditorRequestError,
  cancelSchedule,
  publishPost,
  rejectPost,
  schedulePost,
  submitForReview,
  unpublishPost,
} from "../blog-editor-requests";
import type { BlogPost } from "../types";
import type { BlogEditorError } from "./types";
import { locked } from "./use-blog-post-editor";
import type { BlogReviewActions, UseBlogPostEditorResult } from "./types";

async function publishNowFlow(post: BlogPost): Promise<BlogPost> {
  const submitted = await submitForReview(post.id, null);
  const approved = await approvePost(submitted.id);
  return publishPost(locked(approved));
}

export function useBlogReviewActions(
  editor: UseBlogPostEditorResult,
): BlogReviewActions {
  const [pending, setPending] = useState(false);
  // AE-0438 (F-11): the failed action's error is shown IN the review bar
  // (with its code-specific copy), next to the control that failed.
  const [error, setError] = useState<BlogEditorError | null>(null);

  const run = async (
    task: (post: BlogPost) => Promise<BlogPost>,
  ): Promise<void> => {
    const post = editor.post;
    if (!post || editor.dirty) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      editor.replaceFromServer(await task(post));
    } catch (err) {
      await editor.reload();
      setError(
        err instanceof BlogEditorRequestError
          ? { kind: err.kind, detail: err.detail }
          : { kind: BLOG_EDITOR_ERROR_KINDS.FAILED, detail: null },
      );
    } finally {
      setPending(false);
    }
  };

  return {
    pending,
    error,
    submitForReview: (reviewerId) =>
      run((post) => submitForReview(post.id, reviewerId)),
    approve: () => run((post) => approvePost(post.id)),
    reject: (reason) => run((post) => rejectPost(post.id, reason)),
    publish: () => run((post) => publishPost(locked(post))),
    publishNow: () => run(publishNowFlow),
    unpublish: () => run((post) => unpublishPost(locked(post))),
    schedule: (iso) => run((post) => schedulePost(locked(post), iso)),
    cancelSchedule: () => run((post) => cancelSchedule(locked(post))),
  };
}
