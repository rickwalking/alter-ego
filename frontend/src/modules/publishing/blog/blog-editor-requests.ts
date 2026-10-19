/**
 * Requests of the blog section editor (AE-0424, ADR-0025).
 *
 * Every content write sends `If-Match` (the loaded `lock_version`) and every
 * route answers with the full post, so the editor keeps one source of truth.
 * Failures become a typed `BlogEditorRequestError` the UI maps to copy: a
 * stale lock, a non-migrated row ("migration pending"), a validation error, a
 * status-guard rejection or a failed image/AI call.
 */

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { API_ENDPOINTS, HTTP_METHODS, HTTP_STATUS } from "@/constants/api";
import { HTTP_HEADER_IF_MATCH } from "@/constants/workflow";
import {
  BLOG_EDITOR_ERROR_KINDS,
  BLOG_MIGRATION_PENDING_CODES,
  type BlogEditorErrorKind,
} from "@/constants/blog-editor";
import type {
  BlogContentLanguage,
  BlogImageSlotRef,
} from "./lib/editor-document";
import type { BlogPostVersion } from "./components/types";
import type {
  BlogEditorSettings,
  BlogImagePatch,
  BlogVoicePersona,
  BlogPost,
  BlogPostUpdatePayload,
} from "./types";

const LANGUAGE_PARAM = "language";
const REVIEWER_PARAM = "reviewer_id";
const REASON_PARAM = "reason";

/** A failed editor request: `kind` drives the copy, `detail` is the API code. */
export class BlogEditorRequestError extends Error {
  constructor(
    public readonly kind: BlogEditorErrorKind,
    public readonly detail: string | null,
  ) {
    super(detail ?? kind);
    this.name = "BlogEditorRequestError";
  }
}

async function readDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : null;
  } catch {
    return null;
  }
}

function isMigrationPending(detail: string | null): boolean {
  return BLOG_MIGRATION_PENDING_CODES.some((code) => detail?.startsWith(code));
}

const KIND_BY_STATUS: Record<number, BlogEditorErrorKind> = {
  [HTTP_STATUS.BAD_REQUEST]: BLOG_EDITOR_ERROR_KINDS.STATUS_GUARD,
  [HTTP_STATUS.NOT_FOUND]: BLOG_EDITOR_ERROR_KINDS.NOT_FOUND,
  [HTTP_STATUS.CONFLICT]: BLOG_EDITOR_ERROR_KINDS.CONFLICT,
  [HTTP_STATUS.UNPROCESSABLE_ENTITY]: BLOG_EDITOR_ERROR_KINDS.VALIDATION,
  [HTTP_STATUS.BAD_GATEWAY]: BLOG_EDITOR_ERROR_KINDS.AI_FAILED,
};

/** Map a failed response to its typed error kind. */
export function errorKind(
  status: number,
  detail: string | null,
): BlogEditorErrorKind {
  if (detail === BLOG_EDITOR_ERROR_KINDS.VERSION_CONFLICT) {
    return BLOG_EDITOR_ERROR_KINDS.VERSION_CONFLICT;
  }
  if (
    status === HTTP_STATUS.UNPROCESSABLE_ENTITY &&
    isMigrationPending(detail)
  ) {
    return BLOG_EDITOR_ERROR_KINDS.MIGRATION_PENDING;
  }
  return KIND_BY_STATUS[status] ?? BLOG_EDITOR_ERROR_KINDS.FAILED;
}

async function request<T>(url: string, init: RequestInit): Promise<T> {
  const response = await authenticatedFetch(url, init);
  if (!response.ok) {
    const detail = await readDetail(response);
    throw new BlogEditorRequestError(
      errorKind(response.status, detail),
      detail,
    );
  }
  return (await response.json()) as T;
}

function locked(
  method: string,
  lockVersion: number,
  body?: unknown,
): RequestInit {
  return {
    method,
    headers: { [HTTP_HEADER_IF_MATCH]: String(lockVersion) },
    body: body === undefined ? undefined : JSON.stringify(body),
  };
}

function withQuery(url: string, params: Record<string, string>): string {
  const query = new URLSearchParams(params).toString();
  return query ? `${url}?${query}` : url;
}

function slotUrl(postId: string, slot: BlogImageSlotRef): string {
  const base =
    slot.sectionId === null
      ? API_ENDPOINTS.BLOG_POST_COVER_IMAGE(postId)
      : API_ENDPOINTS.BLOG_POST_SECTION_IMAGE(postId, slot.sectionId);
  return withQuery(base, { [LANGUAGE_PARAM]: slot.language });
}

export interface LockedPost {
  id: string;
  lockVersion: number;
}

export function savePost(
  post: LockedPost,
  payload: BlogPostUpdatePayload,
): Promise<BlogPost> {
  const init = locked(HTTP_METHODS.PUT, post.lockVersion, payload);
  return request<BlogPost>(API_ENDPOINTS.BLOG_POST_BY_ID(post.id), init);
}

export function generateSlotImage(
  post: LockedPost,
  change: { slot: BlogImageSlotRef; prompt: string | null },
): Promise<BlogPost> {
  const init = locked(HTTP_METHODS.POST, post.lockVersion, {
    prompt: change.prompt,
  });
  return request<BlogPost>(slotUrl(post.id, change.slot), init);
}

export function patchSlotImage(
  post: LockedPost,
  change: { slot: BlogImageSlotRef; patch: BlogImagePatch },
): Promise<BlogPost> {
  const init = locked(HTTP_METHODS.PATCH, post.lockVersion, change.patch);
  return request<BlogPost>(slotUrl(post.id, change.slot), init);
}

export function removeSlotImage(
  post: LockedPost,
  slot: BlogImageSlotRef,
): Promise<BlogPost> {
  return request<BlogPost>(
    slotUrl(post.id, slot),
    locked(HTTP_METHODS.DELETE, post.lockVersion),
  );
}

export function rewriteSection(
  post: LockedPost,
  change: {
    language: BlogContentLanguage;
    sectionId: string;
    personaId: string | null;
  },
): Promise<BlogPost> {
  const url = withQuery(
    API_ENDPOINTS.BLOG_POST_SECTION_REWRITE(post.id, change.sectionId),
    {
      [LANGUAGE_PARAM]: change.language,
    },
  );
  const body = { persona_id: change.personaId };
  return request<BlogPost>(
    url,
    locked(HTTP_METHODS.POST, post.lockVersion, body),
  );
}

export function generateEnTranslation(post: LockedPost): Promise<BlogPost> {
  const init = locked(HTTP_METHODS.POST, post.lockVersion);
  return request<BlogPost>(
    API_ENDPOINTS.BLOG_POST_TRANSLATION_EN(post.id),
    init,
  );
}

export function restoreVersion(
  post: LockedPost,
  versionNumber: number,
): Promise<BlogPost> {
  const url = API_ENDPOINTS.BLOG_POST_RESTORE_VERSION(post.id, versionNumber);
  return request<BlogPost>(url, locked(HTTP_METHODS.POST, post.lockVersion));
}

export function submitForReview(
  postId: string,
  reviewerId: string | null,
): Promise<BlogPost> {
  const params: Record<string, string> = reviewerId
    ? { [REVIEWER_PARAM]: reviewerId }
    : {};
  const url = withQuery(API_ENDPOINTS.BLOG_POST_SUBMIT_REVIEW(postId), params);
  return request<BlogPost>(url, { method: HTTP_METHODS.POST });
}

export function approvePost(postId: string): Promise<BlogPost> {
  return request<BlogPost>(API_ENDPOINTS.BLOG_POST_APPROVE(postId), {
    method: HTTP_METHODS.POST,
  });
}

export function rejectPost(postId: string, reason: string): Promise<BlogPost> {
  const url = withQuery(API_ENDPOINTS.BLOG_POST_REJECT(postId), {
    [REASON_PARAM]: reason,
  });
  return request<BlogPost>(url, { method: HTTP_METHODS.POST });
}

export function publishPost(post: LockedPost): Promise<BlogPost> {
  const init = locked(HTTP_METHODS.POST, post.lockVersion);
  return request<BlogPost>(API_ENDPOINTS.BLOG_POST_PUBLISH(post.id), init);
}

export function unpublishPost(post: LockedPost): Promise<BlogPost> {
  const init = locked(HTTP_METHODS.POST, post.lockVersion);
  return request<BlogPost>(API_ENDPOINTS.BLOG_POST_UNPUBLISH(post.id), init);
}

export function schedulePost(
  post: LockedPost,
  scheduledAtIso: string,
): Promise<BlogPost> {
  const body = { scheduled_publish_at: scheduledAtIso };
  const init = locked(HTTP_METHODS.POST, post.lockVersion, body);
  return request<BlogPost>(API_ENDPOINTS.BLOG_SCHEDULE(post.id), init);
}

export function cancelSchedule(post: LockedPost): Promise<BlogPost> {
  const init = locked(HTTP_METHODS.DELETE, post.lockVersion);
  return request<BlogPost>(API_ENDPOINTS.BLOG_SCHEDULE(post.id), init);
}

export function fetchEditorSettings(): Promise<BlogEditorSettings> {
  return request<BlogEditorSettings>(API_ENDPOINTS.BLOG_EDITOR_SETTINGS, {
    method: HTTP_METHODS.GET,
  });
}

export function fetchVersions(postId: string): Promise<BlogPostVersion[]> {
  return request<BlogPostVersion[]>(API_ENDPOINTS.BLOG_POST_VERSIONS(postId), {
    method: HTTP_METHODS.GET,
  });
}

/** The personas the owner can rewrite in (first one is the default voice). */
export async function fetchVoicePersonas(): Promise<BlogVoicePersona[]> {
  const page = await request<{ items: BlogVoicePersona[] }>(
    API_ENDPOINTS.PERSONAS,
    {
      method: HTTP_METHODS.GET,
    },
  );
  return page.items;
}
