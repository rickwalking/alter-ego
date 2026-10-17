/**
 * Single-post blog requests used by the editor (AE-0411).
 *
 * The editor loads the post through the detail endpoint (the list endpoint
 * returns summaries without `content`, and only the first page), and maps
 * save failures to typed errors so the UI can show them.
 */

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { API_ENDPOINTS, HTTP_STATUS } from "@/constants/api";
import { HTTP_HEADER_IF_MATCH } from "@/constants/workflow";
import {
  BLOG_POST_ERR_VALIDATION,
  BLOG_POST_ERR_VERSION_CONFLICT,
  BlogPostMutationError,
} from "./constants";
import type { BlogPost, BlogPostUpdatePayload } from "./types";

const ERR_LOAD_FAILED = "Failed to load blog post";
const ERR_SAVE_FAILED = "Failed to save blog post";

export const blogPostKeys = {
  detail: (id: string) => ["blog-post", id] as const,
};

/** GET /api/blog-posts/{id} — `null` when the post does not exist. */
export async function fetchBlogPostDetail(
  id: string,
): Promise<BlogPost | null> {
  const response = await authenticatedFetch(API_ENDPOINTS.BLOG_POST_BY_ID(id));
  if (response.status === HTTP_STATUS.NOT_FOUND) {
    return null;
  }
  if (!response.ok) {
    throw new Error(ERR_LOAD_FAILED);
  }
  return (await response.json()) as BlogPost;
}

/** PUT /api/blog-posts/{id} with If-Match; typed errors for 409 / 422. */
export async function saveBlogPost(
  id: string,
  payload: BlogPostUpdatePayload,
  lockVersion: number,
): Promise<BlogPost> {
  const response = await authenticatedFetch(API_ENDPOINTS.BLOG_POST_BY_ID(id), {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      [HTTP_HEADER_IF_MATCH]: String(lockVersion),
    },
    body: JSON.stringify(payload),
  });
  if (response.status === HTTP_STATUS.CONFLICT) {
    throw new BlogPostMutationError(BLOG_POST_ERR_VERSION_CONFLICT);
  }
  if (response.status === HTTP_STATUS.UNPROCESSABLE_ENTITY) {
    throw new BlogPostMutationError(BLOG_POST_ERR_VALIDATION);
  }
  if (!response.ok) {
    throw new Error(ERR_SAVE_FAILED);
  }
  return (await response.json()) as BlogPost;
}
