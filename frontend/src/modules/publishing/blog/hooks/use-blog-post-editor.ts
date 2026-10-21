"use client";

/**
 * Blog section editor state (AE-0411 load/save; AE-0424 `blog.v2` draft).
 *
 * Loads the FULL post through the detail endpoint and edits a draft
 * `{ title, excerpt, document }` over the strict `blog.v2` document, one
 * content language at a time (PT or EN). A save PUTs only what changed with
 * `If-Match`; a conflict keeps the owner's unsaved draft, typing done while
 * the PUT is in flight is kept, and a 409 caused by our own slot write is
 * retried on top. Slot actions (image, rewrite, translation) apply their
 * server answer to just that slot (`lib/editor-session.ts`). A row that is still legacy markdown is never
 * parsed here: it surfaces as "migration pending" (AC15).
 */

import { useEffect, useRef, useState } from "react";
import type { MutableRefObject } from "react";
import { useQuery } from "@tanstack/react-query";

import { BLOG_EDITOR_ERROR_KINDS } from "@/constants/blog-editor";
import { isGenerationInProgress } from "../generation/generation-state";
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
import {
  ownBumpRetry,
  sessionAfterSave,
  sessionAfterSlot,
  sessionFromPost,
} from "../lib/editor-session";
import {
  BLOG_CONTENT_PT,
  type BlogContentLanguage,
} from "../lib/editor-document";
import type { BlogPost, BlogPostUpdatePayload } from "../types";
import type {
  BlogEditorError,
  DraftMerge,
  EditorPersistence,
  EditorPersistenceDeps,
  DraftState,
  EditorSession,
  UseBlogPostEditorResult,
} from "./types";

function isVersionConflict(err: unknown): boolean {
  return (
    err instanceof BlogEditorRequestError &&
    err.kind === BLOG_EDITOR_ERROR_KINDS.VERSION_CONFLICT
  );
}

/** PUT `payload`; on a 409 caused by our own slot write, retry on top once. */
async function saveWithOwnBumpRetry(
  session: EditorSession,
  payload: BlogPostUpdatePayload,
  latest: () => EditorSession | null,
): Promise<{ saved: BlogPost; sent: BlogEditorDraft | null }> {
  try {
    return {
      saved: await savePost(locked(session.base), payload),
      sent: session.draft,
    };
  } catch (err) {
    const retry = isVersionConflict(err)
      ? ownBumpRetry(session.base.lock_version, latest())
      : null;
    if (!retry) {
      throw err;
    }
    const current = latest()?.base ?? session.base;
    if (!retry.payload) {
      return { saved: current, sent: retry.draft };
    }
    const lock = { id: session.base.id, lockVersion: retry.lockVersion };
    return { saved: await savePost(lock, retry.payload), sent: retry.draft };
  }
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

/** A first load, another post, or a newer version while either copy generates. */
function shouldAdoptLoaded(
  session: EditorSession | null,
  loaded: BlogPost,
): boolean {
  if (session?.base.id !== loaded.id) {
    return true;
  }
  const newer = session.base.lock_version !== loaded.lock_version;
  return (
    newer &&
    (isGenerationInProgress(session.base) || isGenerationInProgress(loaded))
  );
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
  // AE-0425: the generation run owns the document while it writes it. A newer
  // server version is adopted (replacing the read-only session) when EITHER
  // copy is generating: the editor's copy (the run's writes, then its final
  // status) or the server's (a Retry clicked here flipped it to in_progress,
  // so the editor locks at once instead of staying editable on "failed").
  if (loaded && shouldAdoptLoaded(session, loaded)) {
    setSession(sessionFromPost(loaded));
  }
  return { query, session, setSession };
}

/** Save (with the own-bump 409 retry) and version restore for one session. */
/** Restore a stored version into the session (null on success). */
async function restoreSessionVersion(
  session: EditorSession | null,
  versionNumber: number,
  setSession: EditorPersistenceDeps["setSession"],
): Promise<BlogEditorError | null> {
  if (!session) {
    return { kind: BLOG_EDITOR_ERROR_KINDS.FAILED, detail: null };
  }
  try {
    const restored = await restoreVersion(locked(session.base), versionNumber);
    setSession(sessionFromPost(restored));
    return null;
  } catch (err) {
    return toEditorError(err);
  }
}

/** The draft, its validation and the pending update payload (if dirty). */
function draftState(session: EditorSession | null): DraftState {
  const draft = session?.draft ?? null;
  const original = session?.original ?? null;
  return {
    draft,
    validation: draft ? validateBlogEditorDraft(draft) : null,
    payload: draft && original ? buildBlogPostUpdate(original, draft) : null,
  };
}

function useEditorPersistence({
  session,
  setSession,
  latest,
  payload,
  validation,
}: EditorPersistenceDeps): EditorPersistence {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<BlogEditorError | null>(null);
  const persist = async (): Promise<BlogPost | null> => {
    if (!session) {
      return null;
    }
    if (!payload) {
      return latest.current?.base ?? session.base;
    }
    if (validation && hasValidationErrors(validation)) {
      return null;
    }
    setSaving(true);
    setError(null);
    try {
      const { saved, sent } = await saveWithOwnBumpRetry(
        session,
        payload,
        () => latest.current,
      );
      setSession((prev) => sessionAfterSave(prev, saved, sent));
      return saved;
    } catch (err) {
      setError(toEditorError(err));
      return null;
    } finally {
      setSaving(false);
    }
  };

  const handleRestore = (versionNumber: number) =>
    restoreSessionVersion(session, versionNumber, setSession);

  return { persist, handleRestore, saving, error, setError };
}

/** A ref that always holds the last committed value. */
function useLatest<T>(value: T): MutableRefObject<T> {
  const ref = useRef<T>(value);
  useEffect(() => {
    ref.current = value;
  }, [value]);
  return ref;
}

export function useBlogPostEditor(postId: string): UseBlogPostEditorResult {
  const { query, session, setSession } = useEditorSession(postId);
  // The latest committed session, for answers that arrive after a re-render
  // (a 409 retry, the lock an action must use).
  const latest = useLatest(session);
  const [language, setLanguage] =
    useState<BlogContentLanguage>(BLOG_CONTENT_PT);
  const { draft, validation, payload } = draftState(session);

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
    setSession((prev) => sessionAfterSlot(prev, post, merge));
  };

  const { persist, handleRestore, saving, error, setError } =
    useEditorPersistence({ session, setSession, latest, payload, validation });

  return {
    post: session?.base,
    loading: query.isPending && postId !== "",
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
