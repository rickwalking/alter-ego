"use client";

/**
 * Blog section editor state (AE-0411 load/save; AE-0424 `blog.v2` draft).
 *
 * Loads the FULL post through the detail endpoint and edits a draft
 * `{ title, excerpt, document }` over the strict `blog.v2` document, one
 * content language at a time (PT or EN). A save PUTs only what changed with
 * `If-Match`; a conflict keeps the owner's unsaved draft. Slot actions (image,
 * rewrite, translation) apply their server answer to just that slot, so typing
 * elsewhere is never lost. A row that is still legacy markdown is never
 * parsed here: it surfaces as "migration pending" (AC15).
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { BLOG_EDITOR_ERROR_KINDS } from "@/constants/blog-editor";
import { blogPostKeys, fetchBlogPostDetail } from "../blog-post-requests";
import {
  BlogEditorRequestError,
  restoreVersion,
  savePost,
  type LockedPost,
} from "../blog-editor-requests";
import {
  buildBlogPostUpdate,
  hasValidationErrors,
  validateBlogEditorDraft,
  type BlogEditorDraft,
} from "../editor-content";
import { tryParseBlogContent } from "../lib/parse-blog-content";
import {
  BLOG_CONTENT_PT,
  type BlogContentLanguage,
} from "../lib/editor-document";
import type { BlogPost } from "../types";
import type {
  BlogEditorError,
  DraftMerge,
  EditorSession,
  UseBlogPostEditorResult,
} from "./types";

function draftFromPost(post: BlogPost): BlogEditorDraft | null {
  const document = tryParseBlogContent(post.content);
  if (!document) {
    return null;
  }
  return { title: post.title, excerpt: post.excerpt ?? "", document };
}

function sessionFromPost(post: BlogPost): EditorSession {
  const original = draftFromPost(post);
  return { base: post, original, draft: original };
}

function toEditorError(err: unknown): BlogEditorError {
  if (err instanceof BlogEditorRequestError) {
    return { kind: err.kind, detail: err.detail };
  }
  return { kind: BLOG_EDITOR_ERROR_KINDS.FAILED, detail: null };
}

export function locked(post: BlogPost): LockedPost {
  return { id: post.id, lockVersion: post.lock_version };
}

function useEditorSession(postId: string) {
  const query = useQuery({
    queryKey: blogPostKeys.detail(postId),
    queryFn: () => fetchBlogPostDetail(postId),
    enabled: Boolean(postId),
  });
  const loaded = query.data ?? null;
  const [session, setSession] = useState<EditorSession | null>(null);
  // Adjust state while rendering (not in an effect): start a session the
  // first time a post loads; later server answers update it explicitly.
  if (loaded && session?.base.id !== loaded.id) {
    setSession(sessionFromPost(loaded));
  }
  return { query, session, setSession };
}

export function useBlogPostEditor(postId: string): UseBlogPostEditorResult {
  const { query, session, setSession } = useEditorSession(postId);
  const [language, setLanguage] =
    useState<BlogContentLanguage>(BLOG_CONTENT_PT);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<BlogEditorError | null>(null);
  const draft = session?.draft ?? null;
  const original = session?.original ?? null;
  const validation = draft ? validateBlogEditorDraft(draft) : null;
  const payload =
    draft && original ? buildBlogPostUpdate(original, draft) : null;

  const updateDraft = (
    edit: (current: BlogEditorDraft) => BlogEditorDraft,
  ): void => {
    setSession((prev) =>
      prev?.draft ? { ...prev, draft: edit(prev.draft) } : prev,
    );
  };

  const replaceFromServer = (post: BlogPost): void =>
    setSession(sessionFromPost(post));

  const applyServerPost = (post: BlogPost, merge: DraftMerge): void => {
    setSession((prev) => mergeServerPost(prev, post, merge));
  };

  const persist = async (): Promise<BlogPost | null> => {
    if (!session) {
      return null;
    }
    if (!payload) {
      return session.base;
    }
    if (validation && hasValidationErrors(validation)) {
      return null;
    }
    setSaving(true);
    setError(null);
    try {
      const saved = await savePost(locked(session.base), payload);
      replaceFromServer(saved);
      return saved;
    } catch (err) {
      setError(toEditorError(err));
      return null;
    } finally {
      setSaving(false);
    }
  };

  const handleRestore = async (versionNumber: number): Promise<boolean> => {
    if (!session) {
      return false;
    }
    setError(null);
    try {
      replaceFromServer(
        await restoreVersion(locked(session.base), versionNumber),
      );
      return true;
    } catch (err) {
      setError(toEditorError(err));
      return false;
    }
  };

  return {
    post: session?.base,
    loading: query.isPending && Boolean(postId),
    loadFailed: query.isError,
    draft,
    language,
    setLanguage,
    updateDraft,
    validation,
    dirty: payload !== null,
    saving,
    error,
    setError,
    handleSave: async () => (await persist()) !== null,
    ensureSaved: async () => {
      const saved = await persist();
      return saved ? locked(saved) : null;
    },
    applyServerPost,
    replaceFromServer,
    reload: async () => {
      const result = await query.refetch();
      if (result.data) {
        replaceFromServer(result.data);
      }
    },
    handleRestore,
  };
}

/** The new session after a slot action: base/original from the server, the
 * draft keeps the owner's other edits and takes only the merged slot. */
function mergeServerPost(
  prev: EditorSession | null,
  post: BlogPost,
  merge: DraftMerge,
): EditorSession {
  const next = sessionFromPost(post);
  if (!prev?.draft || !next.original) {
    return next;
  }
  const document = merge(prev.draft.document, next.original.document);
  return { ...next, draft: { ...prev.draft, document } };
}
