/**
 * AE-0446: the blog-post list/mutation requests behind ``useBlogPosts``, as
 * plain functions (status mapping and error messages unchanged).
 */
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { API_BASE, HTTP_STATUS } from "@/constants/api";
import { HTTP_HEADER_IF_MATCH } from "@/constants/workflow";
import type {
  BlogPost,
  BlogPostCreatePayload,
  BlogPostUpdatePayload,
} from "./types";
import {
  BLOG_POST_ERR_CAROUSEL_DELETE_BLOCKED,
  BLOG_POST_ERR_SLUG_CONFLICT,
  BLOG_POST_ERR_VALIDATION,
  BlogPostMutationError,
} from "./constants";
import type { BlogPostFilters } from "./hooks/types";

const POSTS_URL = `${API_BASE}/blog-posts`;
const JSON_HEADERS = { "Content-Type": "application/json" };

export interface BlogPostPage {
  items: BlogPost[];
  total: number;
}

/** The outcome of a delete: done, blocked by its carousel, or a stale lock. */
export type BlogPostDeleteOutcome =
  | "deleted"
  | "carouselBlocked"
  | "versionConflict";

function postUrl(id: string, action?: string): string {
  return action ? `${POSTS_URL}/${id}/${action}` : `${POSTS_URL}/${id}`;
}

function ifMatch(lockVersion: number): Record<string, string> {
  return { [HTTP_HEADER_IF_MATCH]: String(lockVersion) };
}

async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : null;
  } catch {
    return null;
  }
}

function listQuery(filters: BlogPostFilters): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.search) params.set("search", filters.search);
  if (filters.limit) params.set("limit", String(filters.limit));
  if (filters.offset) params.set("offset", String(filters.offset));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export async function fetchBlogPostPage(
  filters: BlogPostFilters,
): Promise<BlogPostPage> {
  const response = await authenticatedFetch(
    `${POSTS_URL}${listQuery(filters)}`,
  );
  if (!response.ok) {
    throw new Error("Failed to fetch blog posts");
  }
  const data = (await response.json()) as { items: BlogPost[]; total?: number };
  return { items: data.items, total: data.total ?? data.items.length };
}

export async function createBlogPost(
  data: BlogPostCreatePayload,
): Promise<BlogPost> {
  const response = await authenticatedFetch(POSTS_URL, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(data),
  });
  if (response.status === HTTP_STATUS.CONFLICT) {
    throw new BlogPostMutationError(BLOG_POST_ERR_SLUG_CONFLICT);
  }
  if (response.status === HTTP_STATUS.UNPROCESSABLE_ENTITY) {
    throw new BlogPostMutationError(BLOG_POST_ERR_VALIDATION);
  }
  if (!response.ok) throw new Error("Failed to create blog post");
  return (await response.json()) as BlogPost;
}

export async function updateBlogPost(
  id: string,
  change: { data: BlogPostUpdatePayload; lockVersion: number },
): Promise<BlogPost> {
  const response = await authenticatedFetch(postUrl(id), {
    method: "PUT",
    headers: { ...JSON_HEADERS, ...ifMatch(change.lockVersion) },
    body: JSON.stringify(change.data),
  });
  if (!response.ok) throw new Error("Failed to update blog post");
  return (await response.json()) as BlogPost;
}

export async function deleteBlogPost(
  id: string,
  lockVersion: number,
): Promise<BlogPostDeleteOutcome> {
  const response = await authenticatedFetch(postUrl(id), {
    method: "DELETE",
    headers: ifMatch(lockVersion),
  });
  if (response.status === HTTP_STATUS.CONFLICT) {
    const detail = await readErrorDetail(response);
    return detail === BLOG_POST_ERR_CAROUSEL_DELETE_BLOCKED
      ? "carouselBlocked"
      : "versionConflict";
  }
  if (!response.ok) throw new Error("Failed to delete blog post");
  return "deleted";
}

/** null when the lock version was stale (409). */
export async function unpublishBlogPost(
  id: string,
  lockVersion: number,
): Promise<BlogPost | null> {
  const response = await authenticatedFetch(postUrl(id, "unpublish"), {
    method: "POST",
    headers: ifMatch(lockVersion),
  });
  if (response.status === HTTP_STATUS.CONFLICT) {
    return null;
  }
  if (!response.ok) throw new Error("Failed to unpublish blog post");
  return (await response.json()) as BlogPost;
}

/** POST a workflow transition (submit-review / approve / publish). */
export async function postBlogPostAction(
  id: string,
  { action, failure }: { action: string; failure: string },
): Promise<void> {
  const response = await authenticatedFetch(postUrl(id, action), {
    method: "POST",
  });
  if (!response.ok) throw new Error(failure);
}
