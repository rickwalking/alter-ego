"use client";

/**
 * Blog post editor state hook (AE-0155 route-page thinning).
 *
 * Owns the editor composition that previously lived inline in
 * `app/dashboard/blog-posts/[id]/edit/page.tsx`: it loads the post via
 * {@link useBlogPosts}, mirrors its editable fields into local state, and
 * exposes the save + version-restore handlers. The route page becomes thin
 * composition over this contract; behavior is byte-identical.
 */

import { useEffect, useState } from "react";

import type { BlogPostVersion } from "../components/types";
import { useBlogPosts } from "./use-blog-posts";
import type { UseBlogPostEditorResult } from "./types";

const DEFAULT_LOCK_VERSION = 1;

export function useBlogPostEditor(postId: string): UseBlogPostEditorResult {
  const { posts, loading, update, refetch } = useBlogPosts();
  const [title, setTitle] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [bodyText, setBodyText] = useState("");
  const [selectedText, setSelectedText] = useState("");
  const [lockVersion, setLockVersion] = useState(DEFAULT_LOCK_VERSION);
  const [saving, setSaving] = useState(false);

  const post = posts.find((item) => item.id === postId);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  useEffect(() => {
    if (!post) {
      return;
    }
    setTitle(post.title);
    setExcerpt(post.excerpt ?? "");
    const body =
      typeof post.content?.body === "string" ? post.content.body : "";
    setBodyText(body);
    setLockVersion(post.lock_version ?? DEFAULT_LOCK_VERSION);
  }, [post]);

  const handleSave = async (): Promise<void> => {
    if (!postId) {
      return;
    }
    setSaving(true);
    try {
      await update(
        postId,
        {
          title,
          excerpt,
          content: { body: bodyText },
        },
        lockVersion,
      );
      await refetch();
    } finally {
      setSaving(false);
    }
  };

  const handleRestore = (version: BlogPostVersion): void => {
    setTitle(version.title);
    setExcerpt(version.excerpt ?? "");
    const body =
      typeof version.snapshot?.body === "string" ? version.snapshot.body : "";
    setBodyText(body);
  };

  return {
    post,
    loading,
    saving,
    title,
    setTitle,
    excerpt,
    setExcerpt,
    bodyText,
    setBodyText,
    selectedText,
    setSelectedText,
    handleSave,
    handleRestore,
  };
}
