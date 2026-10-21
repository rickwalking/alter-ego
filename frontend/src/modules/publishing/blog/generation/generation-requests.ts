/**
 * Blog generation requests (ADR-0025).
 *
 * All three routes answer 202 with the draft id; the caller navigates to the
 * editor, which polls the post while `generation.status` is in progress.
 * `from-carousel` answers 409 with the existing post id when the carousel
 * already has a blog post (then the caller opens that post instead).
 */

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { API_ENDPOINTS, HTTP_METHODS, HTTP_STATUS } from "@/constants/api";
import { ERR_BLOG_POST_EXISTS_FOR_PROJECT } from "./generation-constants";

const ERR_GENERATION_FAILED = "Failed to start blog generation";
const JSON_HEADERS = { "Content-Type": "application/json" };

export interface GenerationAccepted {
  kind: "accepted";
  id: string;
  attempt: number;
  warnings: string[];
}

export interface GenerationExists {
  kind: "exists";
  id: string;
}

interface AcceptedBody {
  id: string;
  generation: { attempt: number; warnings?: string[] };
}

interface ConflictBody {
  code?: string;
  post_id?: string;
}

/** The request failed; `status` is the HTTP status. */
export class BlogGenerationRequestError extends Error {
  constructor(readonly status: number) {
    super(ERR_GENERATION_FAILED);
    this.name = "BlogGenerationRequestError";
  }
}

async function accepted(response: Response): Promise<GenerationAccepted> {
  if (response.status !== HTTP_STATUS.ACCEPTED) {
    throw new BlogGenerationRequestError(response.status);
  }
  const body = (await response.json()) as AcceptedBody;
  return {
    kind: "accepted",
    id: body.id,
    attempt: body.generation.attempt,
    warnings: body.generation.warnings ?? [],
  };
}

async function post(url: string, payload?: unknown): Promise<Response> {
  return authenticatedFetch(url, {
    method: HTTP_METHODS.POST,
    headers: JSON_HEADERS,
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
}

/** POST /api/blog-posts/from-carousel — a draft, or the existing post. */
export async function generateBlogFromCarousel(
  projectId: string,
): Promise<GenerationAccepted | GenerationExists> {
  const response = await post(API_ENDPOINTS.BLOG_POST_FROM_CAROUSEL, {
    project_id: projectId,
  });
  if (response.status === HTTP_STATUS.CONFLICT) {
    const body = (await response.json()) as ConflictBody;
    if (body.code === ERR_BLOG_POST_EXISTS_FOR_PROJECT && body.post_id) {
      return { kind: "exists", id: body.post_id };
    }
    throw new BlogGenerationRequestError(response.status);
  }
  return accepted(response);
}

/** POST /api/blog-posts/generate — a standalone draft from a topic. */
export async function generateStandaloneBlogPost(
  topic: string,
): Promise<GenerationAccepted> {
  return accepted(await post(API_ENDPOINTS.BLOG_POST_GENERATE, { topic }));
}

/** POST /api/blog-posts/{id}/generation/retry — same row, new attempt. */
export async function retryBlogGeneration(
  postId: string,
): Promise<GenerationAccepted> {
  return accepted(await post(API_ENDPOINTS.BLOG_POST_GENERATION_RETRY(postId)));
}
