import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  BLOG_POST_ERR_SLUG_CONFLICT,
  BlogPostMutationError,
} from "@/modules/publishing";
import type { BlogPost } from "@/modules/publishing";

// Scenarios: see tests/features/blog-dashboard-ae0411.feature
// ("Creating a post that fails shows an error", "Dashboard copy is localized")

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

import { useNewBlogPost } from "@/app/dashboard/blog-posts/use-new-blog-post";

beforeEach(() => {
  push.mockReset();
});

describe("useNewBlogPost (AE-0411)", () => {
  it("creates a localized untitled draft with a body and opens the editor", async () => {
    const create = vi.fn().mockResolvedValue({ id: "new-1" } as BlogPost);
    const { result } = renderHook(() => useNewBlogPost(create));
    await act(async () => {
      await result.current.handleNewPost();
    });
    expect(create).toHaveBeenCalledWith({
      title: "Untitled draft",
      content: { body: "" },
      excerpt: "",
    });
    expect(push).toHaveBeenCalledWith("/dashboard/blog-posts/new-1/edit");
    expect(result.current.createError).toBeNull();
  });

  it("shows a create error and re-enables the button on failure", async () => {
    const create = vi.fn().mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useNewBlogPost(create));
    await act(async () => {
      await result.current.handleNewPost();
    });
    expect(result.current.creating).toBe(false);
    expect(result.current.createError).toBe(
      "Could not create the post. Try again.",
    );
    expect(push).not.toHaveBeenCalled();
  });

  it("explains a slug conflict", async () => {
    const create = vi
      .fn()
      .mockRejectedValue(
        new BlogPostMutationError(BLOG_POST_ERR_SLUG_CONFLICT),
      );
    const { result } = renderHook(() => useNewBlogPost(create));
    await act(async () => {
      await result.current.handleNewPost();
    });
    expect(result.current.createError).toMatch(/already uses this slug/);
  });
});
