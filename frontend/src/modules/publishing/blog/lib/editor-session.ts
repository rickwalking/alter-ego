/**
 * Pure session transitions of the blog editor.
 *
 * A session is `{ base, original, draft }`: the last server post, the draft as
 * that post reads, and the owner's edited draft. Every server answer goes
 * through one of these so no keystroke is dropped:
 * - after a save, a draft that changed while the PUT was in flight is kept;
 * - after a slot action, only that slot is merged into the current draft;
 * - a save that lost the race to our OWN slot write is retried once on top of
 *   the newer lock (the draft already contains the merged slot).
 */

import { buildBlogPostUpdate, type BlogEditorDraft } from "../editor-content";
import { tryParseBlogContent } from "./parse-blog-content";
import type { BlogDocument } from "@/schemas/blog-document";
import type { BlogPost, BlogPostUpdatePayload } from "../types";

export interface EditorSessionState {
  base: BlogPost;
  /** `null` when the stored content is not `blog.v2` (migration pending). */
  original: BlogEditorDraft | null;
  draft: BlogEditorDraft | null;
}

export type DraftMergeFn = (
  draftDoc: BlogDocument,
  serverDoc: BlogDocument,
) => BlogDocument;

function draftFromPost(post: BlogPost): BlogEditorDraft | null {
  const document = tryParseBlogContent(post.content);
  if (!document) {
    return null;
  }
  return { title: post.title, excerpt: post.excerpt ?? "", document };
}

export function sessionFromPost(post: BlogPost): EditorSessionState {
  const original = draftFromPost(post);
  return { base: post, original, draft: original };
}

/** The session after a save of `sent`: typing done meanwhile is kept. */
export function sessionAfterSave(
  prev: EditorSessionState | null,
  saved: BlogPost,
  sent: BlogEditorDraft | null,
): EditorSessionState {
  const next = sessionFromPost(saved);
  if (!prev?.draft || prev.draft === sent || !next.original) {
    return next;
  }
  return { ...next, draft: prev.draft };
}

/** The session after a slot action: only the merged slot changes the draft. */
export function sessionAfterSlot(
  prev: EditorSessionState | null,
  post: BlogPost,
  merge: DraftMergeFn,
): EditorSessionState {
  const next = sessionFromPost(post);
  if (!prev?.draft || !next.original) {
    return next;
  }
  const document = merge(prev.draft.document, next.original.document);
  return { ...next, draft: { ...prev.draft, document } };
}

export interface SaveRetry {
  lockVersion: number;
  payload: BlogPostUpdatePayload | null;
  draft: BlogEditorDraft | null;
}

/**
 * A 409 on save is our own doing when the latest session moved past the lock
 * the PUT was sent with (only our slot answers move `base`): retry on top.
 */
export function ownBumpRetry(
  sentLock: number,
  latest: EditorSessionState | null,
): SaveRetry | null {
  if (!latest?.original || !latest.draft) {
    return null;
  }
  if (latest.base.lock_version <= sentLock) {
    return null;
  }
  return {
    lockVersion: latest.base.lock_version,
    payload: buildBlogPostUpdate(latest.original, latest.draft),
    draft: latest.draft,
  };
}
