"use client";

/**
 * Blog post editor state hook (AE-0155 route-page thinning; AE-0411 fixes).
 *
 * Loads the FULL post through the detail endpoint (the list only carries
 * summaries without `content`, and only its first page), mirrors the editable
 * fields into local state, and saves only what changed. The body is read from
 * either stored shape (`content.body` or a carousel row's `content.markdown`)
 * and written back without dropping any other content key, so a title-only
 * save never touches the stored content (B05). Client validation mirrors the
 * backend 422 rules and save failures are returned, never thrown (B19).
 */

import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import type { BlogPostVersion } from "../components/types";
import {
  blogPostKeys,
  fetchBlogPostDetail,
  saveBlogPost,
} from "../blog-post-requests";
import { BlogPostMutationError } from "../constants";
import {
  buildBlogPostUpdate,
  hasValidationErrors,
  readEditableBody,
  validateBlogEditorFields,
} from "../editor-content";
import type { BlogPost } from "../types";
import type { BlogEditorSaveError, UseBlogPostEditorResult } from "./types";

const DEFAULT_LOCK_VERSION = 1;
const SAVE_FAILED: BlogEditorSaveError = "failed";

function toSaveError(err: unknown): BlogEditorSaveError {
  return err instanceof BlogPostMutationError ? err.code : SAVE_FAILED;
}

export function useBlogPostEditor(postId: string): UseBlogPostEditorResult {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: blogPostKeys.detail(postId),
    queryFn: () => fetchBlogPostDetail(postId),
    enabled: Boolean(postId),
  });
  const post = query.data ?? undefined;
  const [title, setTitle] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [bodyText, setBodyText] = useState("");
  const [selectedText, setSelectedText] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<BlogEditorSaveError | null>(null);

  useEffect(() => {
    if (!post) {
      return;
    }
    setTitle(post.title);
    setExcerpt(post.excerpt ?? "");
    setBodyText(readEditableBody(post.content).text);
  }, [post]);

  const fields = { title, excerpt, bodyText };
  const validation = validateBlogEditorFields(fields);

  const persist = async (loaded: BlogPost): Promise<boolean> => {
    const payload = buildBlogPostUpdate(
      {
        title: loaded.title,
        excerpt: loaded.excerpt ?? "",
        content: loaded.content ?? {},
      },
      fields,
    );
    if (!payload) {
      return true;
    }
    const saved = await saveBlogPost(
      postId,
      payload,
      loaded.lock_version ?? DEFAULT_LOCK_VERSION,
    );
    queryClient.setQueryData(blogPostKeys.detail(postId), saved);
    return true;
  };

  const handleSave = async (): Promise<boolean> => {
    if (!post || hasValidationErrors(validation)) {
      return false;
    }
    setSaving(true);
    setSaveError(null);
    try {
      return await persist(post);
    } catch (err) {
      setSaveError(toSaveError(err));
      return false;
    } finally {
      setSaving(false);
    }
  };

  const handleRestore = (version: BlogPostVersion): void => {
    setTitle(version.title);
    setExcerpt(version.excerpt ?? "");
    setBodyText(readEditableBody(version.snapshot).text);
  };

  return {
    post,
    loading: query.isPending && Boolean(postId),
    loadFailed: query.isError,
    saving,
    title,
    setTitle,
    excerpt,
    setExcerpt,
    bodyText,
    setBodyText,
    selectedText,
    setSelectedText,
    validation,
    saveError,
    handleSave,
    handleRestore,
  };
}
