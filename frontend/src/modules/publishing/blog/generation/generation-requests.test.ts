import { beforeEach, describe, expect, it, vi } from "vitest";

/** Gherkin: tests/features/blog_generate_ae0425.feature. */

vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: vi.fn(),
}));

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import {
  BlogGenerationRequestError,
  generateBlogFromCarousel,
  generateStandaloneBlogPost,
  retryBlogGeneration,
} from "./generation-requests";

const mockFetch = vi.mocked(authenticatedFetch);

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const ACCEPTED = {
  id: "post-1",
  generation: {
    status: "in_progress",
    attempt: 1,
    warnings: ["carousel_private"],
  },
};

beforeEach(() => {
  mockFetch.mockReset();
});

describe("blog generation requests (AE-0425)", () => {
  it("posts the project id and returns the new draft", async () => {
    mockFetch.mockResolvedValue(jsonResponse(ACCEPTED, 202));
    const result = await generateBlogFromCarousel("proj-1");
    expect(mockFetch).toHaveBeenCalledWith("/api/blog-posts/from-carousel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: "proj-1" }),
    });
    expect(result).toEqual({
      kind: "accepted",
      id: "post-1",
      attempt: 1,
      warnings: ["carousel_private"],
    });
  });

  it("returns the existing post on the 409", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse(
        { code: "blog_post_exists_for_project", post_id: "old" },
        409,
      ),
    );
    await expect(generateBlogFromCarousel("proj-1")).resolves.toEqual({
      kind: "exists",
      id: "old",
    });
  });

  it("throws on any other 409 or error", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "x" }, 409));
    await expect(generateBlogFromCarousel("p")).rejects.toBeInstanceOf(
      BlogGenerationRequestError,
    );
    mockFetch.mockResolvedValue(jsonResponse({ detail: "x" }, 404));
    await expect(generateBlogFromCarousel("p")).rejects.toMatchObject({
      status: 404,
    });
  });

  it("posts a standalone topic", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ id: "s-1", generation: { attempt: 1 } }, 202),
    );
    const result = await generateStandaloneBlogPost("Um tema");
    expect(mockFetch.mock.calls[0]?.[0]).toBe("/api/blog-posts/generate");
    expect(mockFetch.mock.calls[0]?.[1]?.body).toBe(
      JSON.stringify({ topic: "Um tema" }),
    );
    expect(result.warnings).toEqual([]);
  });

  it("retries on the same post id", async () => {
    mockFetch.mockResolvedValue(
      jsonResponse({ id: "post-1", generation: { attempt: 2 } }, 202),
    );
    const result = await retryBlogGeneration("post-1");
    expect(mockFetch.mock.calls[0]?.[0]).toBe(
      "/api/blog-posts/post-1/generation/retry",
    );
    expect(mockFetch.mock.calls[0]?.[1]?.body).toBeUndefined();
    expect(result).toMatchObject({ id: "post-1", attempt: 2 });
  });

  it("rejects a retry that is not accepted", async () => {
    mockFetch.mockResolvedValue(jsonResponse({ detail: "x" }, 409));
    await expect(retryBlogGeneration("post-1")).rejects.toBeInstanceOf(
      BlogGenerationRequestError,
    );
  });
});
