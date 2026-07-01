import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  BLOG_POST_ERR_CAROUSEL_DELETE_BLOCKED,
  BLOG_POST_ERR_VERSION_CONFLICT,
  BlogPostMutationError,
} from "../constants";
import { useBlogPosts } from "./use-blog-posts";

// Scenarios: see tests/features/blog-posts-management.feature

vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: vi.fn(),
}));

import { authenticatedFetch } from "@/lib/authenticated-fetch";

const mockFetch = vi.mocked(authenticatedFetch);

const POST = {
  id: "p-1",
  title: "Post",
  slug: "post",
  status: "published",
  lock_version: 3,
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function listResponse(): Response {
  return jsonResponse({ items: [POST], total: 1 });
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe("useBlogPosts delete (AE-0296)", () => {
  it("sends DELETE with the If-Match header and removes the post", async () => {
    mockFetch.mockResolvedValueOnce(listResponse());
    const { result } = renderHook(() => useBlogPosts());
    await waitFor(() => expect(result.current.posts).toHaveLength(1));

    mockFetch.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await act(async () => {
      await result.current.delete("p-1", 3);
    });

    const [url, init] = mockFetch.mock.calls[1];
    expect(String(url)).toContain("/blog-posts/p-1");
    expect(init?.method).toBe("DELETE");
    expect((init?.headers as Record<string, string>)["If-Match"]).toBe("3");
    expect(result.current.posts).toHaveLength(0);
  });

  it("throws a typed carousel-guard error on 409 carousel_origin_delete_blocked", async () => {
    mockFetch.mockResolvedValueOnce(listResponse());
    const { result } = renderHook(() => useBlogPosts());
    await waitFor(() => expect(result.current.posts).toHaveLength(1));

    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: BLOG_POST_ERR_CAROUSEL_DELETE_BLOCKED }, 409),
    );
    await act(async () => {
      await expect(result.current.delete("p-1", 3)).rejects.toMatchObject({
        code: BLOG_POST_ERR_CAROUSEL_DELETE_BLOCKED,
      });
    });
    // The post is NOT removed on a guard rejection.
    expect(result.current.posts).toHaveLength(1);
  });

  it("refetches and throws version_conflict on a stale delete", async () => {
    mockFetch.mockResolvedValueOnce(listResponse());
    const { result } = renderHook(() => useBlogPosts());
    await waitFor(() => expect(result.current.posts).toHaveLength(1));

    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: BLOG_POST_ERR_VERSION_CONFLICT }, 409),
    );
    mockFetch.mockResolvedValueOnce(listResponse()); // refetch after conflict
    await act(async () => {
      const error = await result.current
        .delete("p-1", 1)
        .catch((e: unknown) => e);
      expect(error).toBeInstanceOf(BlogPostMutationError);
      expect((error as BlogPostMutationError).code).toBe(
        BLOG_POST_ERR_VERSION_CONFLICT,
      );
    });
    // 1 list + 1 delete + 1 refetch
    expect(mockFetch.mock.calls.length).toBeGreaterThanOrEqual(3);
  });
});

describe("useBlogPosts unpublish (AE-0296)", () => {
  it("POSTs /unpublish with If-Match and swaps in the returned post", async () => {
    mockFetch.mockResolvedValueOnce(listResponse());
    const { result } = renderHook(() => useBlogPosts());
    await waitFor(() => expect(result.current.posts).toHaveLength(1));

    mockFetch.mockResolvedValueOnce(
      jsonResponse({ ...POST, status: "draft", lock_version: 4 }),
    );
    await act(async () => {
      await result.current.unpublish("p-1", 3);
    });

    const [url, init] = mockFetch.mock.calls[1];
    expect(String(url)).toContain("/blog-posts/p-1/unpublish");
    expect(init?.method).toBe("POST");
    expect((init?.headers as Record<string, string>)["If-Match"]).toBe("3");
    expect(result.current.posts[0].status).toBe("draft");
    expect(result.current.posts[0].lock_version).toBe(4);
  });

  it("refetches and throws version_conflict on a stale unpublish", async () => {
    mockFetch.mockResolvedValueOnce(listResponse());
    const { result } = renderHook(() => useBlogPosts());
    await waitFor(() => expect(result.current.posts).toHaveLength(1));

    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: BLOG_POST_ERR_VERSION_CONFLICT }, 409),
    );
    mockFetch.mockResolvedValueOnce(listResponse());
    await act(async () => {
      const error = await result.current
        .unpublish("p-1", 1)
        .catch((e: unknown) => e);
      expect(error).toBeInstanceOf(BlogPostMutationError);
    });
  });
});
